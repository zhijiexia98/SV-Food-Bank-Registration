# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#   * Rearrange models' order
#   * Make sure each model has one field with primary_key=True
#   * Make sure each ForeignKey and OneToOneField has `on_delete` set to the desired behavior
#   * Remove `managed = False` lines if you wish to allow Django to create, modify, and delete the table
# Feel free to rename the models, but don't rename db_table values or field names.
from django.db import models
from django.utils.timezone import now


class AdminLogs(models.Model):
    admin = models.ForeignKey('Users', models.DO_NOTHING)
    action = models.CharField(max_length=255)
    target_id = models.IntegerField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    logged_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'admin_logs'


class Category(models.Model):
    category = models.CharField(unique=True, max_length=255)
    points = models.IntegerField(blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'category'


class Donations(models.Model):
    donor = models.ForeignKey('Users', models.DO_NOTHING)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    message = models.TextField(blank=True, null=True)
    donated_at = models.DateTimeField(default=now)

    class Meta:
        # managed = False
        db_table = 'donations'


class FoodPackages(models.Model):
    package_name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    quantity = models.IntegerField()
    price_per_package = models.DecimalField(max_digits=10, decimal_places=2)
    total_cost = models.DecimalField(max_digits=10, decimal_places=2)
    purchased_at = models.DateTimeField(blank=True, null=True)
    admin = models.ForeignKey('Users', models.DO_NOTHING)

    class Meta:
        # managed = False
        db_table = 'food_packages'


class Requests(models.Model):
    student = models.ForeignKey('Users', models.DO_NOTHING)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    status = models.CharField(max_length=8, blank=True, null=True)
    requested_at = models.DateTimeField(blank=True, null=True)
    processed_at = models.DateTimeField(blank=True, null=True)
    admin = models.ForeignKey('Users', models.DO_NOTHING, related_name='requests_admin_set', blank=True, null=True)
    package = models.ForeignKey(FoodPackages, models.DO_NOTHING, blank=True, null=True)
    request_id = models.IntegerField(unique=True, blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'requests'


class Student(models.Model):
    student_id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    email = models.CharField(unique=True, max_length=255)
    point = models.IntegerField(blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'student'


class Users(models.Model):
    username = models.CharField(unique=True, max_length=255)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=7)
    email = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=20, blank=True, null=True)
    balance = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    is_active = models.IntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)
    point = models.IntegerField(blank=True, null=True)
    student_id = models.IntegerField(unique=True, blank=True, null=True)

    class Meta:
        # managed = False
        db_table = 'users'
