from rest_framework import serializers
from .models import ResearchProject, ResearchImage, Annotation


class AnnotationSerializer(serializers.ModelSerializer):
    """Serializer for individual annotations"""
    
    class Meta:
        model = Annotation
        fields = ['id', 'image', 'session_id', 'left', 'top', 'width', 'height', 'text', 'created_at']
        read_only_fields = ['id', 'created_at']

    def validate(self, data):
        """Validate annotation bounds"""
        if data.get('left', 0) < 0 or data.get('top', 0) < 0:
            raise serializers.ValidationError("Position values cannot be negative")
        
        if data.get('width', 0) <= 0 or data.get('height', 0) <= 0:
            raise serializers.ValidationError("Width and height must be positive")
        
        return data


class ResearchImageSerializer(serializers.ModelSerializer):
    """Full serializer for research images with computed URL"""
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
    """Full serializer for research projects with nested images"""
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

    def validate_name(self, value):
        """Ensure project name is not empty"""
        if not value or not value.strip():
            raise serializers.ValidationError("Project name cannot be empty")
        return value.strip()


class AnnotationSubmitSerializer(serializers.Serializer):
    """
    Serializer for submitting a batch of annotations from review page.
    Expects data in the following format:
    {
        "id": "image-uuid",
        "image_href": "url-to-image",
        "text_content": "optional description",
        "annotations": [
            {
                "target": {...},
                "body": [...]
            },
            ...
        ]
    }
    """
    id = serializers.CharField(help_text="Unique identifier for the image")
    image_href = serializers.CharField(help_text="URL reference to the image")
    text_content = serializers.CharField(
        allow_blank=True,
        required=False,
        help_text="Optional text content or description"
    )
    annotations = serializers.ListField(
        child=serializers.DictField(),
        allow_empty=True,
        help_text="List of annotations in Annotorious format"
    )

    def validate_id(self, value):
        """Validate that the ID is a valid UUID"""
        try:
            import uuid
            uuid.UUID(value)
        except (ValueError, AttributeError):
            raise serializers.ValidationError("Invalid UUID format for image ID")
        return value

    def validate_annotations(self, value):
        """Validate that annotations have the required structure"""
        for idx, annotation in enumerate(value):
            if not isinstance(annotation, dict):
                raise serializers.ValidationError(f"Annotation {idx} must be a dictionary")
            
            # Check for required keys
            if 'target' not in annotation:
                raise serializers.ValidationError(f"Annotation {idx} missing 'target' field")
        
        return value

    def create(self, validated_data):
        """
        This method is not used for creating annotations directly.
        Annotation creation is handled in the view to maintain session_id consistency.
        """
        raise NotImplementedError(
            "Use the submit_annotations view to create annotations from this serializer"
        )
