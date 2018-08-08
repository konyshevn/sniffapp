from django.contrib import admin

# Register your models here.

from upload_file.models import Uid, Transfer, Traffic


class UidAdmin(admin.ModelAdmin):
    list_display = ('name', 'uid')
    search_fields = ('name', 'uid')


class TransferAdmin(admin.ModelAdmin):
    list_display = ('pc_name', 'mac_addr', 'date_db', 'uid')


class TrafficAdmin(admin.ModelAdmin):
    list_display = ('datetime', 'src', 'dst', 'pkt_size', 'transfer')


admin.site.register(Uid, UidAdmin)
admin.site.register(Transfer, TransferAdmin)
admin.site.register(Traffic, TrafficAdmin)
