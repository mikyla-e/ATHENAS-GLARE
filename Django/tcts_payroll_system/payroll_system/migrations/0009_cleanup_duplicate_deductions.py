# This will be 000X_cleanup_duplicate_deductions.py in your migrations folder
from django.db import migrations

def cleanup_duplicate_deductions(apps, schema_editor):
    """
    Find and clean up duplicate deductions (same type for same payroll record).
    For each set of duplicates, we keep the one with the highest amount.
    """
    Deduction = apps.get_model('payroll_system', 'Deduction')
    PayrollRecord = apps.get_model('payroll_system', 'PayrollRecord')
    
    # First, get all payroll records
    for record in PayrollRecord.objects.all():
        # For each deduction type, check if we have duplicates
        for deduction_type in ['SSS', 'PHILHEALTH', 'PAGIBIG', 'OTHERS']:
            # Get all deductions of this type for this record
            deductions = Deduction.objects.filter(
                payroll_record=record,
                deduction_type=deduction_type
            ).order_by('-amount')  # Order by amount descending
            
            # If we have more than one, keep only the one with the highest amount
            if deductions.count() > 1:
                # Keep the first one (highest amount) and delete the rest
                keep_deduction = deductions.first()
                deductions.exclude(pk=keep_deduction.pk).delete()

class Migration(migrations.Migration):

    dependencies = [
        # Replace 'previous_migration' with the name of your previous migration
        ('payroll_system', '0008_alter_deduction_unique_together'),
    ]

    operations = [
        migrations.RunPython(cleanup_duplicate_deductions),
    ]
