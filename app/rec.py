import datetime
import os
import pickle
import signal
import subprocess
from pathlib import Path
import sqlite3
import owncloud


def rec_video(name):
    # Déclaration de variable
    ts = datetime.datetime.now().timestamp()
    timestamp = datetime.datetime.now()
    jour = timestamp.strftime('%d-%m-%y %Hh%M')

    # Création dossier
    path = Path('/api/rec_tmp/')
    path.mkdir(parents=True, exist_ok=True)

    # Flux réseau caméra
    ip_cam = "192.168.1.142"
    rstp_server = 'rtsp://admin@' + ip_cam + '/0/av0'

    # Check if cam is connected
    ret = os.system("ping -c 3 " + ip_cam + "")
    if ret != 0:
        return False, "Camera not connected."

    # Nom fichier
    file_name = name + ' ' + jour + '.mp4'
    file_source = '/api/rec_tmp/' + file_name

    # Démarrage VLC
    cmdbase = 'flatpak run org.videolan.VLC -I dummy ' + rstp_server + ' --sout="#transcode{vcodec=h264,acodec=mp3,vb=500,fps=30.0}:std{mux=mp4,dst=' + file_source + ',access=file}"'
    process = subprocess.Popen(cmdbase, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True, preexec_fn=os.setsid)
    pid = os.getpgid(process.pid)

    f = open('/api/var_tmp/out.ser', "wb")
    pickler = pickle.Pickler(f, pickle.HIGHEST_PROTOCOL)
    pickler.dump(pid)
    pickler.dump(file_source)
    pickler.dump(file_name)
    f.close()

    # Vérification du démarrage de l'enregistrement

    # Mise en BDD
    con = sqlite3.connect("/api/bdd/rec_bdd.db")
    cur = con.cursor()

    cur.execute('''CREATE TABLE IF NOT EXISTS rec(
        id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
        name TEXT,
        file TEXT,
        time INTEGER,
        status INTEGER
    )''')
    donnees = (name, file_name, ts, 1)
    cur.execute("INSERT INTO rec (name, file, time, status) VALUES (?, ?, ?, ?)", donnees)
    con.commit()
    con.close()

    return True, pid


def unrec_video():
    login = 'Simon'
    password = 'tchaik0123'
    url_nextcloud = 'https://cloud.aymeric-mai.fr/'
    datetime.datetime.now().timestamp()
    timestamp = datetime.datetime.now()
    annee = timestamp.strftime('%Y')
    semaine = timestamp.strftime('%V le %m.%y')

    con = sqlite3.connect("/api/bdd/rec_bdd.db")
    cur = con.cursor()
    f = open('/api/var_tmp/out.ser', "rb")

    unpickler = pickle.Unpickler(f)
    pid = unpickler.load()
    file_source = unpickler.load()
    f.close()

    try:
        os.killpg(pid, signal.SIGTERM)
    except ProcessLookupError:
        pass

    # Use owncloud library for create dir of file mp4
    try:
        oc = owncloud.Client(url_nextcloud)
        oc.login(login, password)
    except:
        pass

    try:
        oc.mkdir('Simon/Vidéos-Simon/' + annee + '')
    except:
        pass

    try:
        oc.mkdir('Simon/Vidéos-Simon/' + annee + '/Semaine-' + semaine + '')
    except:
        pass

    # Pour une utilisation de la library python
    # oc.drop_file('/home/aymeric/Codage/AEVE-REC-API/app/test.txt')

    cur.execute("UPDATE rec SET status = 0 ORDER BY id DESC LIMIT 1")
    con.commit()

    # Verify status is change to 0
    cur.execute("SELECT id FROM rec WHERE status = 1 ORDER BY id DESC LIMIT 1")
    data = cur.fetchall()

    # Replace all database status with 0 if replace uniquely last ID not working
    if len(data) != 0:
        cur.execute("UPDATE rec SET status = 0")
        con.commit()

    con.close()

    # Supprimer le fichier vidéo temporaire
    # if os.path.exists(file_source):
    #    os.remove(file_source)

    return file_source


def status_rec():
    con = sqlite3.connect("/api/bdd/rec_bdd.db")
    cur = con.cursor()
    cur.execute('''CREATE TABLE IF NOT EXISTS rec(
            id INTEGER PRIMARY KEY AUTOINCREMENT UNIQUE,
            name TEXT,
            file TEXT,
            time INTEGER,
            status INTEGER
        )''')
    con.commit()
    cur.execute("SELECT id FROM rec WHERE status = 1 ORDER BY id DESC LIMIT 1")
    data = cur.fetchall()

    # true = enregistrement en cours / false = pas d'enregistrement en cours
    if len(data) == 0:
        rec = 'false'
    else:
        rec = 'true'
        rec_id = (','.join(map(str, next(zip(*data)))))

    try:
        return rec, rec_id
    except NameError:
        return rec


def info_rec(rec_id):
    con = sqlite3.connect("/api/bdd/rec_bdd.db")
    cur = con.cursor()
    cur.execute("SELECT * FROM rec WHERE id = ?", (rec_id,))
    res = cur.fetchall()
    for row in res:
        rec_id = row[0]
        rec_name = row[1]
        rec_file = row[2]
        rec_time = row[3]
        if row[4] == 1:
            rec_status = 'true'
        else:
            rec_status = 'false'
    con.close()

    return rec_id, rec_name, rec_file, rec_time, rec_status


def upload_file():
    cmd_upload = '/api/cron/AEVE-REC_Cron.bash >> /var/log/AEVE-REC_Cron.txt'
    script = subprocess.Popen(cmd_upload, stdin=subprocess.PIPE, stdout=subprocess.PIPE, shell=True)
    script = "True"
    return script
