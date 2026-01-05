from rest_framework import serializers
from .models import ResearchProject, ResearchImage, Annotation


class AnnotationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Annotation
        fields = ['id', 'image', 'session_id', 'left', 'top', 'width', 'height', 'text', 'created_at']
        read_only_fields = ['id', 'created_at']


class ResearchImageSerializer(serializers.ModelSerializer):
    url = serializers.SerializerMethodField()
    review_count = serializers.ReadOnlyField()

    class Meta:
        model = ResearchImage
        fields = ['id', 'project', 'name', 'question', 'image', 'url', 'added_at', 'is_hidden', 'review_count']
        read_only_fields = ['id', 'added_at', 'review_count']

    def get_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.url


class ResearchImageListSerializer(serializers.ModelSerializer):
    """Lighter serializer for nested use in project list"""
    url = serializers.SerializerMethodField()
    review_count = serializers.ReadOnlyField()

    class Meta:
        model = ResearchImage
        fields = ['id', 'name', 'question', 'url', 'added_at', 'is_hidden', 'review_count']

    def get_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return obj.url


class ResearchProjectSerializer(serializers.ModelSerializer):
    images = ResearchImageListSerializer(many=True, read_only=True)

    class Meta:
        model = ResearchProject
        fields = ['id', 'name', 'description', 'created_at', 'is_hidden', 'images']
        read_only_fields = ['id', 'created_at']


class ResearchProjectCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating/updating projects (without nested images)"""
    class Meta:
        model = ResearchProject
        fields = ['id', 'name', 'description', 'is_hidden']
        read_only_fields = ['id']


class AnnotationSubmitSerializer(serializers.Serializer):
    """Serializer for submitting a batch of annotations from review page"""
    id = serializers.CharField()  # uniqueId from frontend
    image_href = serializers.CharField()
    text_content = serializers.CharField(allow_blank=True)
    annotations = serializers.ListField(child=serializers.DictField())

    def create(self, validated_data):
        image_id = validated_data['id']
        session_id = validated_data.get('session_id', str(__import__('uuid').uuid4()))
        annotations_data = validated_data['annotations']

        created_annotations = []
        for ann in annotations_data:
            # Parse Annotorious format
            target = ann.get('target', {})
            selector = target.get('selector', {})
            
            # Get geometry from selector
            geometry = selector.get('geometry', {})
            bounds = geometry.get('bounds', {})
            
            # Get comment text from bodies
            text = ''
            for body in ann.get('body', []):
                if body.get('purpose') == 'commenting':
                    text = body.get('value', '')
                    break

            annotation = Annotation.objects.create(
                image_id=image_id,
                session_id=session_id,
                left=bounds.get('minX', 0),
                top=bounds.get('minY', 0),
                width=bounds.get('maxX', 0) - bounds.get('minX', 0),
                height=bounds.get('maxY', 0) - bounds.get('minY', 0),
                text=text
            )
            created_annotations.append(annotation)

        return created_annotations
