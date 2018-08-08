from django.db import models

# Create your models here.


class Uid(models.Model):
    name = models.CharField(max_length=50)
    uid = models.CharField(primary_key=True, max_length=20)

    def __str__(self):
        return self.name + '(' + self.uid + ')'


class Transfer(models.Model):
    pc_name = models.CharField(max_length=50)
    mac_addr = models.CharField(max_length=17)
    date_db = models.DateTimeField()
    uid = models.ForeignKey(Uid, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.pc_name + ' - ' + str(self.date_db)


class Traffic(models.Model):
    datetime = models.DateTimeField()
    src = models.GenericIPAddressField()
    dst = models.GenericIPAddressField()
    pkt_size = models.FloatField()
    transfer = models.ForeignKey(Transfer, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.src + ' -> ' + self.dst
