from django.db import migrations

class Migration(migrations.Migration):

    dependencies = [
        ("users", "0004_alter_user_options_user_unique_phone_if_not_null_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql=[
                'ALTER TABLE "users_user" ALTER COLUMN "phone" DROP NOT NULL;',
                'ALTER TABLE "users_user" ALTER COLUMN "email" DROP NOT NULL;',
            ],
            reverse_sql=[
                # reverse qilish shart emas, lekin qo'yib qo'ydim
                'ALTER TABLE "users_user" ALTER COLUMN "phone" SET NOT NULL;',
                'ALTER TABLE "users_user" ALTER COLUMN "email" SET NOT NULL;',
            ],
        ),
    ]
