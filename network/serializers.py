import json

from rest_framework import serializers

from . import models


class ExperimentSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Dataset
        # exclude = (
        #     'promoter_intersection', 'promoter_metaplot',
        #     'enhancer_intersection', 'enhancer_metaplot',)


class DatasetSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Dataset
        exclude = (
            'promoter_intersection', 'promoter_metaplot',
            'enhancer_intersection', 'enhancer_metaplot',)


class PCAPlotSerializer(serializers.ModelSerializer):
    pca_plot = serializers.SerializerMethodField('_pca_plot')
    explained_variance = \
        serializers.SerializerMethodField('_explained_variance')
    components = serializers.SerializerMethodField('_components')

    def _pca_plot(self, pca):
        return json.loads(pca.plot)['plot']

    def _explained_variance(self, pca):
        return json.loads(pca.plot)['explained_variance']

    def _components(self, pca):
        return json.loads(pca.plot)['components']

    class Meta:
        model = models.PCA
        fields = ('pca_plot', 'explained_variance', 'components')
