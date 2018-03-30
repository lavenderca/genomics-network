import json

import numpy as np
from celery import group, chain, chord
from celery.decorators import task
from django.db.models import Q

from analysis import metaplot, transcript_coverage
from analysis.normalization import normalize_locus_intersection_values
from analysis.utils import \
    download_dataset_bigwigs, generate_intersection_df, remove_dataset_bigwigs
from network import models
from network.tasks.data_recommendations import \
    update_primary_data_sims_and_recs


def process_dataset_batch(datasets, chunk=100):

    for i in range(0, len(datasets), chunk):

        index_1 = i
        index_2 = min(i + chunk, len(datasets))
        dataset_chunk = datasets[index_1:index_2]

        download_dataset_bigwigs(dataset_chunk)

        tasks = []
        for dataset in dataset_chunk:
            tasks.append(process_dataset.s(dataset.pk, download=False))

        job = group(tasks)
        results = job.apply_async()
        results.join()


@task
def process_dataset(dataset_pk, experiment_pk=None, download=True):
    if download:
        chain(
            download_bigwigs.si([dataset_pk]),
            chord(
                process_dataset_intersections([dataset_pk]),
                update_and_clean.si([dataset_pk]),
            ),
        )()
    else:
        chord(
            process_dataset_intersections([dataset_pk]),
            update_and_clean.si([dataset_pk]),
        )()


@task
def download_bigwigs(dataset_pks):
    datasets = models.Dataset.objects.filter(pk__in=dataset_pks)
    download_dataset_bigwigs(datasets)


def process_dataset_intersections(dataset_pks):
    datasets = models.Dataset.objects.filter(pk__in=dataset_pks)
    tasks = []

    for dataset in datasets:
        for lg in models.LocusGroup.objects.filter(
                assembly=dataset.assembly):

            tasks.append(
                update_or_create_dataset_intersection.si(dataset.pk, lg.pk))
            tasks.append(
                update_or_create_dataset_metaplot.si(dataset.pk, lg.pk))

    return group(tasks)


@task
def update_and_clean(dataset_pks, experiment_pk=None):
    datasets = models.Dataset.objects.filter(pk__in=dataset_pks)

    for dataset in datasets:
        assembly = dataset.assembly
        experiment_type = dataset.experiment.experiment_type

        for pca in models.PCA.objects.filter(
            locus_group__assembly=assembly,
            experiment_type=experiment_type,
        ):
            set_pca_transformed_values(dataset, pca)

        for locus_group in models.LocusGroup.objects.filter(
                assembly=dataset.assembly,
        ):
            update_or_create_feature_values(dataset.pk, locus_group.pk)

        dataset.processed = True
        dataset.save()

    remove_bigwigs(dataset_pks)

    if experiment_pk:
        update_primary_data_sims_and_recs(experiment_pk)


def set_pca_transformed_values(dataset, pca):

    dij = models.DatasetIntersectionJson.objects.get(
        dataset=dataset, locus_group=pca.locus_group)

    order = models.PCALocusOrder.objects.filter(pca=pca).order_by('order')
    loci = [x.locus for x in order]

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


@task
def remove_bigwigs(dataset_pks):
    datasets = models.Dataset.objects.filter(pk__in=dataset_pks)
    remove_dataset_bigwigs(datasets)


@task
def update_or_create_dataset_intersection(dataset_pk, locus_group_pk):
    dataset = models.Dataset.objects.get(pk=dataset_pk)
    locus_group = models.LocusGroup.objects.get(pk=locus_group_pk)

    lg_bed_path = locus_group.intersection_bed_path
    bigwig_paths = dataset.generate_local_bigwig_paths()

    loci = models.Locus.objects.filter(group=locus_group).order_by('pk')
    locus_values = transcript_coverage.get_locus_values(
        loci,
        lg_bed_path,
        ambiguous_bigwig=bigwig_paths['ambiguous'],
        plus_bigwig=bigwig_paths['plus'],
        minus_bigwig=bigwig_paths['minus'],
    )
    normalized_values = normalize_locus_intersection_values(loci, locus_values)

    intersection_values = {
        'locus_pks': [],
        'raw_values': [],
        'normalized_values': [],
    }
    for locus in loci:
        intersection_values['locus_pks'].append(locus.pk)
        intersection_values['raw_values'].append(locus_values[locus])
        intersection_values['normalized_values'].append(
            normalized_values[locus])

    models.DatasetIntersectionJson.objects.update_or_create(
        dataset=dataset,
        locus_group=locus_group,
        defaults={
            'intersection_values': json.dumps(intersection_values),
        }
    )


@task
def update_or_create_dataset_metaplot(dataset_pk, locus_group_pk):
    dataset = models.Dataset.objects.get(pk=dataset_pk)
    locus_group = models.LocusGroup.objects.get(pk=locus_group_pk)

    lg_bed_path = locus_group.metaplot_bed_path
    bigwig_paths = dataset.generate_local_bigwig_paths()

    metaplot_out = metaplot.get_metaplot_values(
        locus_group,
        bed_path=lg_bed_path,
        ambiguous_bigwig=bigwig_paths['ambiguous'],
        plus_bigwig=bigwig_paths['plus'],
        minus_bigwig=bigwig_paths['minus'],
    )

    models.MetaPlot.objects.update_or_create(
        dataset=dataset,
        locus_group=locus_group,
        defaults={
            'metaplot': json.dumps(metaplot_out),
        },
    )


def update_all_feature_attributes():
    for locus_group in models.LocusGroup.objects.all():
        for experiment_type in models.ExperimentType.objects.all():
            if models.Dataset.objects.filter(
                assembly=locus_group.assembly,
                experiment__experiment_type=experiment_type,
                experiment__project__isnull=False,
            ).exists():
                update_or_create_feature_attributes.si(
                    locus_group.pk, experiment_type.pk).delay()


@task
def update_or_create_feature_attributes(locus_group_pk, experiment_type_pk):
    locus_group = models.LocusGroup.objects.get(pk=locus_group_pk)
    experiment_type = models.ExperimentType.objects.get(pk=experiment_type_pk)

    datasets = models.Dataset.objects.filter(experiment__project__isnull=False)
    loci = models.Locus.objects.filter(Q(group=locus_group) & (
        Q(transcript__selecting__isnull=False) | Q(enhancer__isnull=False)))

    df = generate_intersection_df(
        locus_group, experiment_type, datasets=datasets, loci=loci)

    feature_attributes = dict()
    for locus in loci:
        values = df.loc[locus.pk]
        feature_attributes[locus.pk] = {
            'name': locus.get_name(),
            'maximum': max(values),
            'minimum': min(values),
            'mean': np.mean(values),
            'median': np.median(values),
            'standard_deviation': np.std(values),
        }

    models.FeatureAttributes.objects.update_or_create(
        locus_group=locus_group,
        experiment_type=experiment_type,
        defaults={
            'feature_attributes': json.dumps(feature_attributes),
        },
    )


def update_all_feature_values():
    for dataset in models.Dataset.objects.all():
        for locus_group in models.LocusGroup.objects.filter(
                assembly=dataset.assembly):
            update_or_create_feature_values.si(
                dataset.pk, locus_group.pk).delay()


@task
def update_or_create_feature_values(dataset_pk, locus_group_pk):
    dataset = models.Dataset.objects.get(pk=dataset_pk)
    locus_group = models.LocusGroup.objects.get(pk=locus_group_pk)

    feature_values = {
        'locus_pks': [],
        'names': [],
        'values': [],
        'max_values': [],
        'min_values': [],
        'medians': [],
        'means': [],
        'standard_deviations': [],
    }

    feature_attributes = models.FeatureAttributes.objects.get(
        locus_group=locus_group,
        experiment_type=dataset.experiment.experiment_type,
    )
    feature_attributes = json.loads(feature_attributes.feature_attributes)

    dij = models.DatasetIntersectionJson.objects.get(
        dataset=dataset, locus_group=locus_group)
    intersection_values = json.loads(dij.intersection_values)

    for locus_pk, value in zip(
        intersection_values['locus_pks'],
        intersection_values['normalized_values'],
    ):
        if str(locus_pk) in feature_attributes:
            attributes = feature_attributes[str(locus_pk)]

            feature_values['locus_pks'].append(locus_pk)
            feature_values['values'].append(value)

            feature_values['names'].append(attributes['name'])
            feature_values['min_values'].append(attributes['minimum'])
            feature_values['max_values'].append(attributes['maximum'])
            feature_values['medians'].append(attributes['median'])
            feature_values['means'].append(attributes['mean'])
            feature_values['standard_deviations'].append(
                attributes['standard_deviation'])

    models.FeatureValues.objects.update_or_create(
        dataset=dataset,
        locus_group=locus_group,
        defaults={
            'feature_values': json.dumps(feature_values),
        },
    )
