"""
API Views for UX Research Panel.

Authentication:
- Review pages: public (respects is_hidden flag)
- Report pages: admin only
- Admin panel (CRUD operations): admin only
"""
import uuid
from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response

from .models import ResearchProject, ResearchImage, Annotation
from .serializers import (
    ResearchProjectSerializer,
    ResearchProjectCreateSerializer,
    ResearchImageSerializer,
    AnnotationSerializer,
    AnnotationSubmitSerializer,
)
from .authentication import (
    login_admin,
    logout_admin,
    get_current_user,
    is_authenticated,
    admin_required,
)


# =============================================================================
# Authentication Views
# =============================================================================

@api_view(['POST'])
def login(request):
    """
    Login endpoint for admin authentication.
    Returns a token for valid credentials.
    """
    email = request.data.get('email')
    password = request.data.get('password')

    if not email or not password:
        return Response({
            'success': False,
            'message': 'Email and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)

    user, token = login_admin(email, password)
    
    if user and token:
        return Response({
            'success': True,
            'message': 'Login successful',
            'user': user,
            'token': token,
        })

    return Response({
        'success': False,
        'message': 'Invalid credentials'
    }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
def logout(request):
    """Logout endpoint - invalidates the token."""
    from .authentication import get_token_from_request
    token = get_token_from_request(request)
    if token:
        logout_admin(token)
    return Response({
        'success': True,
        'message': 'Logged out successfully'
    })


@api_view(['GET'])
def get_current_session(request):
    """
    Check current authentication status.
    Returns user info if authenticated, or authenticated: false otherwise.
    """
    user = get_current_user(request)
    if user:
        return Response({
            'authenticated': True,
            'user': user
        })
    return Response({
        'authenticated': False,
        'user': None
    })


# =============================================================================
# Project ViewSet (Admin operations require auth)
# =============================================================================

class ResearchProjectViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ResearchProject.
    - list/retrieve: admin only (for admin panel)
    - create/update/delete: admin only
    """
    queryset = ResearchProject.objects.all()
    
    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return ResearchProjectCreateSerializer
        return ResearchProjectSerializer
    
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # All project operations require admin auth
        if not is_authenticated(request):
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Authentication required')

    @action(detail=True, methods=['patch'])
    def visibility(self, request, pk=None):
        """Toggle project visibility"""
        project = self.get_object()
        project.is_hidden = not project.is_hidden
        project.save()
        return Response({'is_hidden': project.is_hidden})


# =============================================================================
# Image ViewSet (Mixed access)
# =============================================================================

class ResearchImageViewSet(viewsets.ModelViewSet):
    """
    ViewSet for ResearchImage.
    - retrieve: public (for review page, respects is_hidden)
    - list/create/delete: admin only
    - update/partial_update: DISABLED (to preserve research integrity)
    """
    queryset = ResearchImage.objects.all()
    serializer_class = ResearchImageSerializer
    
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # Allow public access to retrieve (for review page)
        if self.action == 'retrieve':
            return
        # All other operations require admin auth
        if not is_authenticated(request):
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Authentication required')
    
    def retrieve(self, request, *args, **kwargs):
        """
        Public retrieve for review page.
        Returns 404 if image is hidden or project is hidden.
        """
        instance = self.get_object()
        
        # Check if image or its project is hidden (unless admin)
        if not is_authenticated(request):
            if instance.is_hidden or instance.project.is_hidden:
                return Response(
                    {'error': 'Image not found'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    def update(self, request, *args, **kwargs):
        """
        Disabled to preserve research integrity.
        Once an image/question is created, it cannot be edited
        because reviewers may have already answered the original question.
        """
        return Response(
            {'error': 'Image editing is disabled to preserve research integrity'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    def partial_update(self, request, *args, **kwargs):
        """
        Disabled to preserve research integrity.
        Once an image/question is created, it cannot be edited
        because reviewers may have already answered the original question.
        """
        return Response(
            {'error': 'Image editing is disabled to preserve research integrity'},
            status=status.HTTP_405_METHOD_NOT_ALLOWED
        )

    @action(detail=True, methods=['patch'])
    def visibility(self, request, pk=None):
        """Toggle image visibility (admin only)"""
        image = self.get_object()
        image.is_hidden = not image.is_hidden
        image.save()
        return Response({'is_hidden': image.is_hidden})


# =============================================================================
# Annotation ViewSet (Mixed access)
# =============================================================================

class AnnotationViewSet(viewsets.ModelViewSet):
    """
    ViewSet for Annotation.
    - create: public (for review submissions)
    - list/retrieve/update/delete: admin only
    """
    queryset = Annotation.objects.all()
    serializer_class = AnnotationSerializer
    
    def initial(self, request, *args, **kwargs):
        super().initial(request, *args, **kwargs)
        # Allow public access to create (for review submissions)
        if self.action == 'create':
            return
        # All other operations require admin auth
        if not is_authenticated(request):
            from rest_framework.exceptions import AuthenticationFailed
            raise AuthenticationFailed('Authentication required')


# =============================================================================
# Annotation Submission (Public)
# =============================================================================

@api_view(['POST'])
def submit_annotations(request):
    """
    Public endpoint for submitting annotations from review page.
    Uses AnnotationSubmitSerializer to validate Annotorious format.
    """
    serializer = AnnotationSubmitSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Generate session ID for this submission
    session_id = str(uuid.uuid4())
    
    image_id = serializer.validated_data['id']
    annotations_data = serializer.validated_data['annotations']

    try:
        image = ResearchImage.objects.get(id=image_id)
    except ResearchImage.DoesNotExist:
        return Response(
            {'error': 'Image not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Block submissions for hidden images/projects
    if image.is_hidden or image.project.is_hidden:
        return Response(
            {'error': 'Image not found'},
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

            min_x = bounds.get('minX', 0)
            min_y = bounds.get('minY', 0)
            max_x = bounds.get('maxX', 0)
            max_y = bounds.get('maxY', 0)

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


# =============================================================================
# Report Data (Admin only)
# =============================================================================

@api_view(['GET'])
@admin_required
def get_report_data(request, image_id):
    """
    Get all annotations for an image, formatted for the report page.
    Admin only - returns image details and all associated annotations.
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
