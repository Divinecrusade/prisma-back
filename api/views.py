from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import authenticate
from .models import ResearchProject, ResearchImage, Annotation
from .serializers import (
    ResearchProjectSerializer,
    ResearchProjectCreateSerializer,
    ResearchImageSerializer,
    AnnotationSerializer,
    AnnotationSubmitSerializer,
)


class ResearchProjectViewSet(viewsets.ModelViewSet):
    queryset = ResearchProject.objects.all()

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ResearchProjectCreateSerializer
        return ResearchProjectSerializer

    @action(detail=True, methods=['patch'])
    def visibility(self, request, pk=None):
        """Toggle project visibility"""
        project = self.get_object()
        project.is_hidden = not project.is_hidden
        project.save()
        return Response({'is_hidden': project.is_hidden})


class ResearchImageViewSet(viewsets.ModelViewSet):
    queryset = ResearchImage.objects.all()
    serializer_class = ResearchImageSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_queryset(self):
        queryset = ResearchImage.objects.all()
        project_id = self.request.query_params.get('project_id')
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        return queryset

    @action(detail=True, methods=['patch'])
    def visibility(self, request, pk=None):
        """Toggle image visibility"""
        image = self.get_object()
        image.is_hidden = not image.is_hidden
        image.save()
        return Response({'is_hidden': image.is_hidden})


class AnnotationViewSet(viewsets.ModelViewSet):
    queryset = Annotation.objects.all()
    serializer_class = AnnotationSerializer

    def get_queryset(self):
        queryset = Annotation.objects.all()
        image_id = self.request.query_params.get('image_id')
        if image_id:
            queryset = queryset.filter(image_id=image_id)
        return queryset


@api_view(['POST'])
def submit_annotations(request):
    """
    Submit annotations from the review page.
    Expects data in Annotorious format.
    """
    serializer = AnnotationSubmitSerializer(data=request.data)
    if serializer.is_valid():
        # Generate session ID for this submission
        import uuid
        session_id = str(uuid.uuid4())
        
        image_id = serializer.validated_data['id']
        annotations_data = serializer.validated_data['annotations']

        # Check if image exists
        try:
            image = ResearchImage.objects.get(id=image_id)
        except ResearchImage.DoesNotExist:
            return Response(
                {'error': f'Image with id {image_id} not found'},
                status=status.HTTP_404_NOT_FOUND
            )

        created_annotations = []
        for ann in annotations_data:
            # Parse Annotorious format
            target = ann.get('target', {})
            selector = target.get('selector', {})
            geometry = selector.get('geometry', {})
            bounds = geometry.get('bounds', {})

            # Get comment text from bodies
            text = ''
            for body in ann.get('body', []):
                if body.get('purpose') == 'commenting':
                    text = body.get('value', '')
                    break

            annotation = Annotation.objects.create(
                image=image,
                session_id=session_id,
                left=bounds.get('minX', 0),
                top=bounds.get('minY', 0),
                width=bounds.get('maxX', 0) - bounds.get('minX', 0),
                height=bounds.get('maxY', 0) - bounds.get('minY', 0),
                text=text
            )
            created_annotations.append(annotation)

        return Response({
            'message': 'Annotations submitted successfully',
            'session_id': session_id,
            'count': len(created_annotations)
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
def login(request):
    """Simple login endpoint"""
    email = request.data.get('email')
    password = request.data.get('password')

    # For demo: accept specific credentials
    # In production, use Django's auth system properly
    if email == 'admin@example.com' and password == 'admin123':
        return Response({
            'success': True,
            'message': 'Login successful',
            'user': {'email': email}
        })

    return Response({
        'success': False,
        'message': 'Invalid credentials'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
def get_report_data(request, image_id):
    """Get all annotations for an image, formatted for report page"""
    try:
        image = ResearchImage.objects.get(id=image_id)
    except ResearchImage.DoesNotExist:
        return Response(
            {'error': 'Image not found'},
            status=status.HTTP_404_NOT_FOUND
        )

    annotations = image.annotations.all()

    return Response({
        'uniqueId': str(image.id),
        'imageName': image.name,
        'question': image.question,
        'imageUrl': request.build_absolute_uri(image.image.url) if image.image else None,
        'annotations': [
            {
                'id': str(ann.id),
                'left': ann.left,
                'top': ann.top,
                'width': ann.width,
                'height': ann.height,
                'text': ann.text,
                'sessionId': ann.session_id,
            }
            for ann in annotations
        ]
    })
