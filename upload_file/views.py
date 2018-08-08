from django.shortcuts import render, render_to_response
from django.http import Http404, HttpResponse, HttpResponseRedirect
from django.db.models import Sum, F
# Create your views here.
from upload_file.forms import *
from upload_file.models import *
import sqlite3, os
from lockfile import LockFile
from upload_file.config import *


def exec_query(connection, connection_cursor, sql_query, sql_query_arg='', many=False):
    try:
        if many:
            connection_cursor.executemany(sql_query, sql_query_arg)
        else:
            connection_cursor.execute(sql_query, sql_query_arg)
    except sqlite3.DatabaseError as err:
        return str(err)
    else:
        connection.commit()
        return connection_cursor.fetchall()


def isSQLite3(filename):
    from os.path import isfile, getsize
    if not isfile(filename):
        return False
    if getsize(filename) < 100:
        return False
    with open(filename, 'r', encoding="ISO-8859-1") as f:
        header = f.read(100)
        print(header)
    if header.startswith('SQLite format 3'):
        return True


def handle_uploaded_file(f):
    try:
        file_path = file_dir + f.name
        destination = open(file_path, 'wb+')
        for chunk in f.chunks():
            destination.write(chunk)
        destination.close()
    except Exception as err:
        return str(err)


def handle_selected_files(files):
    status = {}
    for file in files:
        status.update([(file, {'name': file, 'loaded': False, 'errors': []})])
        file_path = file_dir + file

        lock = LockFile(file_path)
        if lock.is_locked():
            status[file]['errors'].append('Файл заблокирован (загружается другим процессом).')
            continue
        else:
            lock.acquire()

        if not isSQLite3(file_path):
            status[file]['errors'].append('Не корректный формат файла.')
            lock.release()
            continue

        conn = sqlite3.connect(file_path)
        cursor = conn.cursor()
        packets_file = exec_query(conn, cursor, query_packets_file)
        transfer_file = exec_query(conn, cursor, query_transfer_file)
        if isinstance(transfer_file, str):
            status[file]['errors'].append(transfer_file)
            lock.release()
            continue
        elif isinstance(packets_file, str):
            status[file]['errors'].append(packets_file)
            lock.release()
            continue

        pc_name = transfer_file[0][0]
        mac_addr = transfer_file[0][1]
        date_db = transfer_file[0][2]
        uid_id = transfer_file[0][3]
        if not uid_id:
            status[file]['errors'].append('Не указан Uid')
            lock.release()
            continue

        if not mac_addr:
            status[file]['errors'].append('Не указан mac-адрес')
            lock.release()
            continue

        if not date_db:
            status[file]['errors'].append('Не указана дата выгрузки')
            lock.release()
            continue

        if Transfer.objects.filter(mac_addr=mac_addr, date_db=date_db):
            status[file]['errors'].append('Данный файл уже загружен -' + mac_addr + ' - ' + date_db)
            lock.release()
            continue

        if not Uid.objects.filter(uid=uid_id):
            uid_obj = Uid(name='Unknown', uid=uid_id)
        else:
            uid_obj = Uid.objects.get(uid=uid_id)
        transfer_obj = Transfer(pc_name=pc_name, mac_addr=mac_addr, date_db=date_db, uid=uid_obj)

        uid_obj.save()
        transfer_obj.save()
        packets_all = []
        for packet in packets_file:
            packets_all.append(Traffic(datetime=packet[0], src=packet[1], dst=packet[2], pkt_size=packet[3], transfer=transfer_obj))

        conn.close()
        lock.release()
#        rm = os.remove(file_path)
#        status[file]['errors'].append(str(rm))
        try:
            os.remove(file_path)
        except Exception as err:
            status[file]['errors'].append('Ошибка удаления файла: ' + str(err))
        else:
            Traffic.objects.bulk_create(packets_all)
            status[file]['loaded'] = True

#        Traffic.objects.bulk_create(packets_all)
#        status[file]['loaded'] = True

    return status


def db_upload(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            huf = handle_uploaded_file(request.FILES['file'])
            if not isinstance(huf, str):
                return HttpResponseRedirect('/db/upload/success')
            else:
                return HttpResponseRedirect('/db/upload/fail')
    else:
        form = UploadFileForm()
    return render(request, 'db_upload_form.html', {'form': form})


def db_upload_success(request):
    return render_to_response('db_upload_success.html',)


def db_upload_fail(request):
    return render_to_response('db_upload_fail.html',)


def db_select_status(request):
    return render_to_response('db_select_status.html', {'status': request.session['status']})


def db_select(request):
    if request.method == 'POST':
        form = SelectFiles(request.POST)
        if form.is_valid():
            selected_files = form.cleaned_data['selected_files']
            status = handle_selected_files(selected_files)
            request.session['status'] = status
#            print(status)
            return HttpResponseRedirect('/db/select/status/')
    else:
        form = SelectFiles()
    return render(request, 'db_select_form.html', {'form': form})


def db_stat(request):
    if request.method == 'POST':
        form = SearchForm(request.POST)
        if form.is_valid():
            cd = form.cleaned_data
            print(cd['uid'])
            filter_vals = {}
            if not cd['src'] == '' and not cd['src'] is None:
                filter_vals.update([('src', cd['src'])])
            if not cd['dst'] == '' and not cd['dst'] is None:
                filter_vals.update([('dst', cd['dst'])])
            if not cd['date_from'] == '' and not cd['date_from'] is None:
                filter_vals.update([('datetime__gte', cd['date_from'])])
            if not cd['date_until'] == '' and not cd['date_until'] is None:
                filter_vals.update([('datetime__lte', cd['date_until'])])
            if not cd['uid'] == '' and not cd['uid'] is None:
                filter_vals.update([('transfer__uid__uid', cd['uid'])])

            search_result = list(Traffic.objects.filter(**filter_vals).values('src', 'dst').annotate(traffic_size=Sum(F('pkt_size') / 1048576)).order_by('-traffic_size'))
            return render(request, 'db_stat_form.html', {'form': form, 'search_result': search_result})
    else:
        form = SearchForm()
    return render(request, 'db_stat_form.html', {'form': form})
