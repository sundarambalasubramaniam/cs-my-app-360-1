from django.db import models

# Create your models here.
class StudentDetails(models.Model):
    user_id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=45, blank=True, null=True)
    last_name = models.CharField(max_length=45, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.first_name or 'Unknown'} {self.last_name or ''}".strip()
    
    class Meta:
        db_table = 'student_details'
        verbose_name = 'Student Detail'
        verbose_name_plural = 'Student Details'
        ordering = ['user_id']
        app_label = 'myapp360'