import uuid
from django.db import models


class ResearchProject(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    created_at = models.DateField(auto_now_add=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name


class ResearchImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    project = models.ForeignKey(
        ResearchProject,
        on_delete=models.CASCADE,
        related_name='images'
    )
    name = models.CharField(max_length=200)
    question = models.TextField()
    image = models.ImageField(upload_to='research_images/')
    added_at = models.DateField(auto_now_add=True)
    is_hidden = models.BooleanField(default=False)

    class Meta:
        ordering = ['-added_at']

    def __str__(self):
        return self.name

    @property
    def review_count(self):
        return self.annotations.values('session_id').distinct().count()

    @property
    def url(self):
        return self.image.url if self.image else None


class Annotation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    image = models.ForeignKey(
        ResearchImage,
        on_delete=models.CASCADE,
        related_name='annotations'
    )
    session_id = models.CharField(max_length=100)  # To group annotations per review session
    left = models.FloatField()
    top = models.FloatField()
    width = models.FloatField()
    height = models.FloatField()
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"Annotation on {self.image.name} ({self.session_id})"
