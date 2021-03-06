import json
import os
import random
from collections import defaultdict

import matplotlib.pyplot as plt
import numpy
import pandas as pd
from celery.decorators import task
from django.conf import settings
from django.db.models import Q
from matplotlib.colors import rgb2hex
from scipy.spatial.distance import mahalanobis
from sklearn.decomposition import PCA
from sklearn.ensemble import RandomForestClassifier

from network.tasks.analysis.utils import (
    generate_intersection_df, generate_pca_transformed_df)
from network import models


def _update_pca(pca_pk, **kwargs):

    pca = models.PCA.objects.get(pk=pca_pk)

    df = get_encode_intersection_df(pca)
    df = filter_intersection(df, pca)

    fit_and_set_pca(pca, df, **kwargs)


def update_pca(locus_group_pk, experiment_type_pk, **kwargs):

    locus_group = models.LocusGroup.objects.get(pk=locus_group_pk)
    experiment_type = models.ExperimentType.objects.get(pk=experiment_type_pk)

    pca = models.PCA.objects.get_or_create(
        locus_group=locus_group, experiment_type=experiment_type)[0]

    df = get_encode_intersection_df(pca)
    df = filter_intersection(df, pca)

    fit_and_set_pca(pca, df, **kwargs)


def get_encode_intersection_df(pca):
    datasets = models.Dataset.objects.filter(
        assembly=pca.locus_group.assembly,
        experiment__experiment_type=pca.experiment_type,
        experiment__project__name='ENCODE',
    )
    return generate_intersection_df(
        pca.locus_group, pca.experiment_type, datasets=datasets)


def filter_intersection(df, pca):

    cell_types = get_df_cell_types(df)
    targets = get_df_targets(df)

    df = filter_intersections_by_selected_loci(df, pca)
    df = filter_intersections_by_values(df, pca)
    df = filter_intersection_by_rf_importances(df, cell_types, targets)
    df = filter_datasets_by_mahal_distance(df)

    return df


def fit_and_set_pca(pca, df):

    fitted_pca_model = fit_pca(df)
    set_fitted_pca_model(pca, fitted_pca_model)
    set_pca_loci(pca, df)

    transform_pca_datasets(pca.pk)
    set_pca_plot(pca)


def get_datasets(pca):
    datasets = models.Dataset.objects.filter(
        pcatransformedvalues__pca=pca,
    )
    return list(sorted(datasets, key=lambda x: x.pk))


@task
def filter_intersections_by_selected_loci(df, pca, size_threshold=200):

    if pca.locus_group.group_type in ['promoter', 'genebody', 'mRNA']:

        query = Q(gene__annotation__assembly=pca.locus_group.assembly)
        query &= Q(selecting__isnull=False)
        for prefix in ['LINC', 'LOC']:
            query &= ~Q(gene__name__startswith=prefix)
        for suffix in ['-AS', '-AS1', '-AS2', '-AS3', '-AS4', '-AS5']:
            query &= ~Q(gene__name__endswith=suffix)

        selected_transcripts = models.Transcript.objects.filter(query)

        selected_locus_pks = models.Locus.objects.filter(
            transcript__in=selected_transcripts,
            group=pca.locus_group,
        ).values_list('pk', flat=True)

        df = df.loc[list(selected_locus_pks)]

        # Filter out shorter transcripts
        if pca.experiment_type.name != 'microRNA-seq':
            selected_transcripts = [
                t for t in selected_transcripts
                if t.end - t.start + 1 >= size_threshold
            ]
            selected_locus_pks = models.Locus.objects.filter(
                transcript__in=selected_transcripts,
                group=pca.locus_group,
            ).values_list('pk', flat=True)
            df = df.loc[list(selected_locus_pks)]

    elif pca.locus_group.group_type in ['enhancer']:
        pass

    return df


@task
def filter_intersections_by_values(df, pca):

    if pca.locus_group.group_type in ['promoter', 'genebody', 'mRNA']:

        # Select 2nd and 3rd quartiles, in terms of variance and signal
        med_iqr = (
            df.median(axis=1).quantile(q=0.25),
            df.median(axis=1).quantile(q=0.75),
        )
        var_iqr = (
            df.var(axis=1).quantile(q=0.25),
            df.var(axis=1).quantile(q=0.75),
        )
        df = df.loc[
            (df.median(axis=1) >= med_iqr[0]) &
            (df.median(axis=1) <= med_iqr[1]) &
            (df.var(axis=1) >= var_iqr[0]) &
            (df.var(axis=1) <= var_iqr[1])
        ]

    elif pca.locus_group.group_type in ['enhancer']:
        pass

    return df


def get_ordered_datasets(df):
    order = df.columns.values.tolist()
    datasets = list(models.Dataset.objects.filter(pk__in=order))
    datasets.sort(key=lambda ds: order.index(ds.pk))
    return datasets


def get_df_cell_types(df):
    datasets = get_ordered_datasets(df)
    cell_types = [ds.experiment.cell_type for ds in datasets]
    return cell_types


def get_df_targets(df):
    datasets = get_ordered_datasets(df)
    targets = [ds.experiment.target for ds in datasets]
    return targets


def filter_intersection_by_rf_importances(df, cell_types, targets, threads=1):
    rf = RandomForestClassifier(n_estimators=1000, n_jobs=threads)

    # Apply to RF classifier, get importances
    data = numpy.transpose(numpy.array(df))
    loci = list(df.index)

    cell_type_importances = rf.fit(
        data, cell_types).feature_importances_

    if set(targets) == {None}:
        totals = cell_type_importances
    else:
        target_importances = rf.fit(
            data, targets).feature_importances_
        totals = [x + y for x, y in zip(cell_type_importances,
                                        target_importances)]

    # Filter by importances
    filtered_loci = \
        [locus for locus, total in sorted(zip(loci, totals),
                                          key=lambda x: -x[1])][:1000]
    return df.loc[filtered_loci]


def filter_datasets_by_mahal_distance(df):

    pca = PCA(n_components=3)
    df_filtered = df

    if df.shape[1] >= 10:

        datasets = df.columns.values.tolist()
        data = numpy.transpose(numpy.array(df))

        fitted = pca.fit_transform(data)

        mean = numpy.mean(fitted, axis=0)
        cov = numpy.cov(fitted, rowvar=False)
        inv = numpy.linalg.inv(cov)

        m_dist = []
        for vector in fitted:
            m_dist.append(mahalanobis(vector, mean, inv))

        Q1 = numpy.percentile(m_dist, 25)
        Q3 = numpy.percentile(m_dist, 75)
        cutoff = Q3 + 1.5 * (Q3 - Q1)

        selected_datasets = []
        for dist, ds in zip(m_dist, datasets):
            if dist < cutoff:
                selected_datasets.append(ds)

        if selected_datasets:
            df_filtered = df[selected_datasets]

    return df_filtered


def fit_pca(df):

    from sklearn.decomposition import PCA

    pca = PCA(n_components=3)
    data = numpy.transpose(numpy.array(df))
    pca.fit(data)

    return pca


def set_fitted_pca_model(pca_object, fitted_pca_model):
    pca_object.pca = fitted_pca_model
    pca_object.save()


def set_pca_loci(pca_object, df):
    pca_object.selected_loci.clear()

    order = list(df.index)
    loci = list(models.Locus.objects.filter(pk__in=order))
    loci.sort(key=lambda locus: order.index(locus.pk))

    pca_locus_orders = []
    for i, locus in enumerate(loci):
        pca_locus_orders.append(models.PCALocusOrder(
            pca=pca_object,
            locus=locus,
            order=i,
        ))
    models.PCALocusOrder.objects.bulk_create(
        pca_locus_orders)


def generate_selected_loci_df(pca, datasets):

    order = models.PCALocusOrder.objects.filter(pca=pca).order_by('order')
    loci = [x.locus for x in order]

    d = {}
    for dij in models.DatasetIntersectionJson.objects.filter(
        locus_group=pca.locus_group,
        dataset__in=datasets,
    ):

        intersection_values = json.loads(dij.intersection_values)

        locus_values = dict()
        for val, pk in zip(
            intersection_values['normalized_values'],
            intersection_values['locus_pks']
        ):
            locus_values[pk] = val

        normalized_values = []
        for locus in loci:
            try:
                normalized_values.append(locus_values[locus.pk])
            except IndexError:
                normalized_values.append(0)

        series = pd.Series(normalized_values)
        d.update({dij.dataset.pk: series})

    df = pd.DataFrame(d)
    df.sort_index(axis=1, inplace=True)

    return df


@task
def transform_pca_datasets(pca_pk):
    pca = models.PCA.objects.get(pk=pca_pk)

    order = models.PCALocusOrder.objects.filter(pca=pca).order_by('order')
    loci = [x.locus for x in order]

    for dij in models.DatasetIntersectionJson.objects.filter(
        locus_group=pca.locus_group,
        dataset__experiment__experiment_type=pca.experiment_type,
    ):

        intersection_values = json.loads(dij.intersection_values)

        locus_values = dict()
        for val, pk in zip(
            intersection_values['normalized_values'],
            intersection_values['locus_pks']
        ):
            locus_values[pk] = val

        normalized_values = []
        for locus in loci:
            try:
                normalized_values.append(locus_values[locus.pk])
            except IndexError:
                normalized_values.append(0)

        transformed_values = pca.pca.transform([normalized_values])[0]
        models.PCATransformedValues.objects.update_or_create(
            pca=pca,
            dataset=dij.dataset,
            defaults={
                'transformed_values': transformed_values.tolist(),
            },
        )


def set_pca_plot(pca):
    pca.plot = json.dumps({
        'plot': get_plot(pca),
        'explained_variance': get_explained_variance(pca),
        'components': get_components(pca),
    })
    pca.save()


def get_plot(pca):

    datasets = list(models.Dataset.objects.filter(
        pcatransformedvalues__pca=pca,
        experiment__project__name='ENCODE',
    ))
    transformed_values = []
    for ds in datasets:
        transformed_values.append(ds.pcatransformedvalues_set
                                  .get(pca=pca).transformed_values)

    cmap = plt.get_cmap('hsv')

    # Set target color scheme
    target_color_path = os.path.join(
        settings.COLOR_KEY_DIR, 'target.json')
    if os.path.exists(target_color_path):
        with open(target_color_path) as f:
            target_to_color = json.load(f)
    else:
        target_set = set([ds.experiment.target for ds in datasets])
        target_to_color = dict()
        for i, target in enumerate(list(target_set)):
            j = i % 20
            index = ((j % 2) * (50) + (j // 2) * (5)) / 100
            target_to_color[target] = rgb2hex(cmap(index))

    # Set cell type color scheme
    cell_type_color_path = os.path.join(
        settings.COLOR_KEY_DIR, 'cell_type.json')
    if os.path.exists(cell_type_color_path):
        with open(cell_type_color_path) as f:
            cell_type_to_color = json.load(f)
    else:
        cell_type_set = set([ds.experiment.cell_type for ds in datasets])
        cell_type_to_color = dict()
        for i, cell_type in enumerate(list(cell_type_set)):
            j = i % 20
            index = ((j % 2) * (50) + (j // 2) * (5)) / 100
            cell_type_to_color[cell_type] = rgb2hex(cmap(index))

    # Create point tag lists
    cell_type_tags = defaultdict(int)
    target_tags = defaultdict(int)
    for ds in datasets:
        cell_type_tags[ds.experiment.cell_type] += 1
        if ds.experiment.target:
            target_tags[ds.experiment.target] += 1
        else:
            target_tags['None'] += 1

    cell_type_tag_list = list([x[0] for x in sorted(
        cell_type_tags.items(), key=lambda x: -x[1])])
    target_tag_list = list([x[0] for x in sorted(
        target_tags.items(), key=lambda x: -x[1])])

    cell_type_tag_colors = []
    for cell_type in cell_type_tag_list:
        if cell_type in cell_type_to_color:
            cell_type_tag_colors.append(cell_type_to_color[cell_type])
        else:
            cell_type_tag_colors.append('#A9A9A9')

    target_tag_colors = []
    for target in target_tag_list:
        if target in target_to_color:
            target_tag_colors.append(target_to_color[target])
        else:
            target_tag_colors.append('#A9A9A9')

    point_tags = {
        'Cell types': list(zip(cell_type_tag_list, cell_type_tag_colors)),
        'Targets': list(zip(target_tag_list, target_tag_colors)),
    }

    # Set available color options
    color_options = ['Cell type']
    if list(target_tags.keys()) != ['None']:
        color_options.append('Target')

    # Set vectors and vector tags
    cell_type_values = defaultdict(list)
    target_values = defaultdict(list)

    for ds, values in zip(datasets, transformed_values):
        cell_type_values[ds.experiment.cell_type].append(values)
        if ds.experiment.target:
            target_values[ds.experiment.target].append(values)

    vectors = []
    vector_tags = {'Cell types': [], 'Targets': []}

    for key, values in sorted(
            cell_type_values.items(), key=lambda x: -len(x[1])):
        if key in cell_type_to_color:
            color = cell_type_to_color[key]
        else:
            color = rgb2hex(cmap(0))
        vectors.append({
            'point': numpy.mean(values, axis=0).tolist(),
            'color': color,
            'label': key,
            'tags': {'Cell type': key},
        })
        vector_tags['Cell types'].append((key, color))

    for key, values in sorted(
            target_values.items(), key=lambda x: -len(x[1])):
        if key in target_to_color:
            color = target_to_color[key]
        else:
            color = rgb2hex(cmap(0))
        vectors.append({
            'point': numpy.mean(values, axis=0).tolist(),
            'color': color,
            'label': key,
            'tags': {'Target': key},
        })
        vector_tags['Targets'].append((key, color))

    # Set points
    points = []
    for ds, values in zip(datasets, transformed_values):
        colors = dict()

        target = ds.experiment.target
        if target in target_to_color:
            colors.update({'Target': target_to_color[target]})
        else:
            colors.update({'Target': '#A9A9A9'})

        cell_type = ds.experiment.cell_type
        if cell_type in cell_type_to_color:
            colors.update({'Cell type': cell_type_to_color[cell_type]})
        else:
            colors.update({'Cell type': '#A9A9A9'})

        points.append({
            'experiment_name': ds.experiment.name,
            'dataset_name': ds.name,
            'experiment_pk': ds.experiment.pk,
            'dataset_pk': ds.pk,
            'experiment_cell_type': ds.experiment.cell_type,
            'experiment_target': ds.experiment.target,
            'transformed_values': values,
            'colors': colors,
            'tags': {
                'Cell type': ds.experiment.cell_type,
                'Target': ds.experiment.target,
            },
        })

    return {
        'points': points,
        'vectors': vectors,
        'point_tags': point_tags,
        'vector_tags': vector_tags,
        'color_options': color_options,
    }


def get_explained_variance(pca):
    return pca.pca.explained_variance_ratio_.tolist()


def get_components(pca):
    components = []

    if pca.locus_group.group_type in ['genebody', 'promoter', 'mRNA']:
        locus_names = [
            x.locus.transcript.gene.name for x in
            models.PCALocusOrder.objects.filter(pca=pca).order_by('order')
        ]
    elif pca.locus_group.group_type in ['enhancer']:
        locus_names = [
            x.locus.enhancer.name for x in
            models.PCALocusOrder.objects.filter(pca=pca).order_by('order')
        ]

    for _component in pca.pca.components_:
        components.append(
            sorted(
                zip(locus_names, _component),
                key=lambda x: -abs(x[1]),
            )[:20]
        )

    return components
