import uuid
from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from .models import ResearchProject, ResearchImage, Annotation
from .serializers import (
    ResearchProjectSerializer,
    ResearchProjectCreateSerializer,
    ResearchImageSerializer,
    AnnotationSerializer,
    AnnotationSubmitSerializer,
)


class ResearchProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing research projects.
    Provides CRUD operations and visibility toggle.
    """
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
    """
    ViewSet for managing research images.
    Supports filtering by project_id and visibility toggle.
    """
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
    """
    ViewSet for managing annotations.
    Supports filtering by image_id.
    """
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
    Expects data in Annotorious format with the following structure:
    {
        "id": "image-uuid",
        "image_href": "url",
        "text_content": "description",
        "annotations": [...]
    }
    """
    serializer = AnnotationSubmitSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Generate session ID for this submission
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
    errors = []

    for idx, ann in enumerate(annotations_data):
        try:
            # Parse Annotorious format
            target = ann.get('target', {})
            selector = target.get('selector', {})
            geometry = selector.get('geometry', {})
            bounds = geometry.get('bounds', {})

            # Validate bounds
            min_x = bounds.get('minX', 0)
            min_y = bounds.get('minY', 0)
            max_x = bounds.get('maxX', 0)
            max_y = bounds.get('maxY', 0)

            # Ensure valid dimensions
            if min_x < 0 or min_y < 0 or max_x < min_x or max_y < min_y:
                errors.append(f"Annotation {idx}: Invalid bounds")
                continue

            # Get comment text from bodies
            text = ''
            for body in ann.get('body', []):
                if body.get('purpose') == 'commenting':
                    text = body.get('value', '')
                    break

            annotation = Annotation.objects.create(
                image=image,
                session_id=session_id,
                left=min_x,
                top=min_y,
                width=max_x - min_x,
                height=max_y - min_y,
                text=text
            )
            created_annotations.append(annotation)

        except Exception as e:
            errors.append(f"Annotation {idx}: {str(e)}")

    response_data = {
        'message': 'Annotations submission completed',
        'session_id': session_id,
        'created_count': len(created_annotations),
        'total_count': len(annotations_data)
    }

    if errors:
        response_data['errors'] = errors

    status_code = status.HTTP_201_CREATED if created_annotations else status.HTTP_400_BAD_REQUEST
    return Response(response_data, status=status_code)


@api_view(['POST'])
def login(request):
    """
    Simple login endpoint.
    TODO: Implement proper authentication with JWT or session-based auth.
    
    For development purposes only. Replace with Django's auth system in production.
    """
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({
            'success': False,
            'message': 'Email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    # TODO: Replace with proper authentication
    # This is a placeholder for development only
    # In production, use Django's authentication system with:
    # - Proper user model
    # - Password hashing
    # - JWT tokens or session authentication
    # - Rate limiting
    
    # Example with Django's auth (commented out for now):
    # user = authenticate(username=email, password=password)
    # if user is not None:
    #     # Create session or JWT token
    #     return Response({'success': True, 'user': {...}})
    
    # Temporary development credentials
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
    """
    Get all annotations for an image, formatted for the report page.
    Returns image details and all associated annotations.
    """
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
                'createdAt': ann.created_at.isoformat(),
            }
            for ann in annotations
        ]
    })
