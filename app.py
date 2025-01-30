from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_file
from flask_bcrypt import Bcrypt
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from functools import wraps
from datetime import datetime, timedelta, date
import logging
from logging.handlers import TimedRotatingFileHandler
from io import BytesIO
import xlsxwriter
import socket
import re
import db
import os

# Inizializzazione del framework
app = Flask(__name__)
#Attivazione cookie temporanei, la sessione si chiude quando il browser si chiude
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'

# Creazione delle istanze per criptare e gestire JWT
bcrypt = Bcrypt(app)
jwt = JWTManager(app)
app.config['JWT_SECRET_KEY'] = os.getenv("JWT_SECRET_KEY") #chiave per la generazione dei token
app.secret_key = os.getenv("FLASK_SECRET_KEY") #chiave per la sessione di flask

#funzione per la gestione del token non valido
@jwt.unauthorized_loader
def custom_unauthorized_response(error_message):
    return render_template('error.html', errore=401)

#Funzione che controlla il login
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Verifica se c'è un token nella sessione
        access_token = session.get('access_token')  # Usa get per evitare eccezioni
        
        if not access_token:
            # Se non c'è il token, redirigi al login
            return render_template('error.html', errore=401)
        
        # Se il token è presente, esegui la funzione richiesta
        return f(*args, **kwargs)

    return decorated_function

logger = None
#Configurazione logger
def configure_logger():
    global logger
    if logger is None:
        logger = logging.getLogger('query_logger')
        logger.setLevel(logging.DEBUG)
        
        #Formattazione corretta delle directory per supportare Windows e Linux
        current_dir = os.path.dirname(os.path.abspath(__file__))
        log_dir = os.path.join(current_dir, 'logs')
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        log_file = os.path.join(log_dir, 'query.log')

        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        #Un log al mese per 3 mesi. 3 log sono tenuti in contemporanea, il più vecchio eliminato automaticamente
        file_handler = TimedRotatingFileHandler(log_file, when='M', interval=1, backupCount=3)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)
#Inizializza il logger
configure_logger()

#Funzione per il reperimento dell'indirizzo ip della macchina
def get_ip():
    hostname = socket.gethostname()
    ip_address = socket.gethostbyname(hostname)
    return ip_address

# region ENDPOINT LATO HTML

# Endpoint principale
@app.route('/')
def index():
    return render_template('index.html')

# Endpoint di login
@app.route('/auth')
def auth():
    return render_template('auth.html')


# Endpoint di ricerca
@app.route('/cerca', methods=['POST'])
def cerca():
    ricerca = request.form.get('ricerca', '').strip()

    if not ricerca:
        return render_template('error.html', errore=1, messaggio="Termine di ricerca non valido.")

    conn, cursor = db.connection_establish()
    if not conn:
        return render_template('error.html', errore=500, messaggio="Errore di connessione al database.")

    try:
        pattern = f"%{ricerca}%"
        query = """
            SELECT 
                c.id AS id_libro,
                c.nome_libro,
                c.autore,
                c.isbn,
                c.genere,
                c.editore, 
                c.anno_pubblicazione,
                c.posizione,
                c.disponibile,
                CASE
                    WHEN c.disponibile = 1 THEN 'Disponibile'
                    ELSE 'In prestito'
                END AS disponibilita
            FROM 
                catalogo c
            WHERE 
                nome_libro LIKE %s 
                OR autore LIKE %s 
                OR genere LIKE %s 
                OR anno_pubblicazione LIKE %s 
                OR editore LIKE %s 
                OR isbn LIKE %s;
        """
        logger.debug(f"IP: {get_ip()} Esecuzione query: {query} con parametri : {(pattern)*6}")
        cursor.execute(query, (pattern,) * 6) #modo più compatto per ripetere il pattern
        risultati = cursor.fetchall()

        if not risultati:
            return render_template('error.html', errore=404, messaggio="Nessun risultato trovato per la ricerca.")
        
        # Conversione in lista di dizionari
        risultati_list = []
        for risultato in risultati:
            risultato_dict = {
                "id_libro": risultato[0],
                "nome_libro": risultato[1],
                "autore": risultato[2],
                "isbn": risultato[3],
                "genere": risultato[4],
                "editore": risultato[5],
                "anno_pubblicazione": risultato[6],
                "posizione": risultato[7],
                "disponibilita": risultato[9],
            }
            risultati_list.append(risultato_dict)

        return render_template('risultati.html', risultati=risultati_list, ricerca=ricerca)

    except Exception as e:
        print(f"Errore del database: {e}")
        return render_template('error.html', errore=500, messaggio="Si è verificato un errore interno.")

    finally:
        if conn:
            conn.close()


#endregion

#region LOGIN

# Endpoint per il login utente
@app.route('/login', methods=['POST'])
def login():
    email = request.form['email']
    password = request.form['password']

    #Definisco la regex per la mail
    regex_email = r"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"

    #Se la mail non verifica la regex
    if not re.match(regex_email,email):
        #Manda un json con errore 403
        return jsonify({"msg": "Inserire email valida"}), 403
    conn, cursor = db.connection_establish()
    if not conn:
        return jsonify({"msg": "Errore di connessione al database"}), 500

    try:
        logger.debug(f"Esecuzione query login dall'IP : {get_ip()} con parametri: {email}")
        cursor.execute("SELECT password FROM utenti WHERE email = %s", (email,))
        user = cursor.fetchone()

        if not user or not bcrypt.check_password_hash(user[0], password):
            return jsonify({"msg": "Email o password errati"}), 401

        # Genera il token con `iat` e `exp`
        iat = datetime.now()
        exp = iat + timedelta(hours=1)  # Valido per 1 ora

        access_token = create_access_token(identity=email, additional_claims={
            "iat": iat.timestamp(),
            "exp": exp.timestamp()
        })

        session['access_token']=access_token
        return render_template('dashboard.html')
    
    except Exception as e:
        print(f"Errore del database: {e}")
        return jsonify({"msg": "Errore durante il login"}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

# Endpoint per il recupero password
@app.route('/recupero_password')
def recupero_password():
    return render_template('recupero_password.html')

# Endpoint protetto per verificare il login
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    utente_corrente = get_jwt_identity()
    return jsonify(logged_in_as=utente_corrente), 200

# Endpoint logout per cancellare la sessione
@app.route('/logout')
def logout():
    # Cancella tutti i dati della sessione, incluso il token
    session.clear()

    # Reindirizza al login
    return redirect(url_for('index'))



#endregion

#region ENDPOINT ADMIN
# Endpoint per l'inserimento di un libro
@app.route('/inserisci_libro', methods=['GET', 'POST'])
@login_required
def inserisci_libro():
    if request.method == 'POST':
        # Ottieni i dati dal form
        nome_libro = request.form['nome_libro']
        autore = request.form['autore']
        isbn = request.form['isbn'].strip()
        genere = request.form['genere']
        editore = request.form['editore']
        anno_pubblicazione = request.form['anno_pubblicazione']
        posizione = request.form['posizione']

        # Connetti al database
        conn, cursor = db.connection_establish()
        if not conn:
            return jsonify({"msg": "Errore di connessione al database"}), 500

        try:
            # Inserisci il libro nella tabella catalogo
            query = """
                INSERT INTO catalogo (nome_libro, autore, isbn, genere, editore, anno_pubblicazione, posizione)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (nome_libro, autore, isbn, genere, editore, anno_pubblicazione, posizione))
            conn.commit()
            return jsonify({"success": True, "msg": "Libro aggiunto con successo"}), 201

        except Exception as e:
            print(f"Errore del database: {e}")
            return jsonify({"success": False, "msg": "Errore durante l'inserimento"}), 500

        finally:
            conn.close()

    return render_template('inserisci_libro.html')

# region PRESTITI
# Endpoint per la gestione dei prestiti
@app.route('/gestisci_prestiti', methods=['GET', 'POST'])
@login_required
def gestisci_prestiti():
    today = date.today()


    conn, cursor = db.connection_establish()
    if not conn:
        return jsonify({"success": False, "msg": "Errore di connessione al database"}), 500

    if request.method == 'POST':
        # Ottieni i dati dal form
        email_utente = request.form['email'].strip()
        isbn = request.form['isbn'].strip()
        data_prestito = request.form['data_prestito']
        data_restituzione = request.form.get('data_restituzione', None)
        data_restituzione_prevista = request.form['data_restituzione_prevista']

        
        
        if not data_restituzione:
            data_restituzione = None

        # Validazione delle date
        #conversione stringa in data    
        inizio = datetime.strptime(data_prestito, '%Y-%m-%d')
        prevista = datetime.strptime(data_restituzione_prevista, '%Y-%m-%d')
        if prevista < inizio:
            return jsonify({"success": False, "msg": "La data di restituzione/prevista deve essere successiva alla data di prestito"}), 400

        try:
            # Recupero id_utente dall'email
            cursor.execute("SELECT id FROM utenti WHERE email = %s", (email_utente,))
            utente = cursor.fetchone()
            if not utente:
                return jsonify({"success": False, "msg": "Utente non trovato"}), 400
            id_utente = utente[0]

            # Recupero id_libro dall'ISBN
            cursor.execute("SELECT id, disponibile FROM catalogo WHERE isbn = %s", (isbn,))
            libro = cursor.fetchone()
            if not libro:
                return jsonify({"success": False, "msg": "Libro non trovato"}), 400
            id_libro, disponibile = libro
            if disponibile != 1:
                return jsonify({"success": False, "msg": "Libro non disponibile perché già in prestito"}), 400

            # Inserimento nuovo prestito
            cursor.execute(
                """
                INSERT INTO prestiti (id_utente, id_libro, data_prestito, data_restituzione, data_restituzione_prevista)
                VALUES (%s, %s, %s, %s, %s)
                """, (id_utente, id_libro, data_prestito, data_restituzione, data_restituzione_prevista)
            )
            # Aggiornamento disponibilità libro
            cursor.execute("UPDATE catalogo SET disponibile = 0 WHERE id = %s", (id_libro,))
            conn.commit()
            return jsonify({"success": True, "msg": "Prestito aggiunto con successo"}), 201

        except Exception as e:
            conn.rollback() # Annullamento in caso di errore durante l'inserimento
            print(f"Errore del database: {e}")
            return jsonify({"success": False, "msg": "Errore durante l'inserimento del prestito"}), 500

    try:
        # Recupero utenti
        cursor.execute("SELECT * FROM utenti")
        utenti = cursor.fetchall()

        # Recupero storico prestiti con calcolo stato
        cursor.execute("""
    SELECT
    prestiti.id AS id_prestito,
    catalogo.id AS id_libro,
    catalogo.nome_libro,
    catalogo.isbn,
    utenti.email,
    utenti.nome_cognome,
    DATE_FORMAT(prestiti.data_prestito, '%d-%m-%Y') AS data_prestito,
    DATE_FORMAT(prestiti.data_restituzione, '%d-%m-%Y') AS data_restituzione,
    DATE_FORMAT(prestiti.data_restituzione_prevista, '%d-%m-%Y') AS data_restituzione_prevista_formattata, -- Alias per la data formattata
    prestiti.promemoria_inviato,
    CASE
        WHEN prestiti.data_restituzione IS NOT NULL THEN 'Terminato'
        WHEN prestiti.data_restituzione_prevista < CURRENT_DATE THEN 'Scaduto'
        ELSE 'In corso'
    END AS stato_prestito
FROM prestiti
JOIN catalogo ON prestiti.id_libro = catalogo.id
JOIN utenti ON prestiti.id_utente = utenti.id;
""")

        prestiti = [dict(zip([column[0] for column in cursor.description], row)) for row in cursor.fetchall()]

        return render_template('gestisci_prestiti.html', utenti=utenti, prestiti=prestiti, today=today)

    except Exception as e:
        print(f"Errore del database: {e}")
        return jsonify({"success": False, "msg": "Errore durante il recupero dei dati"}), 500

    finally:
        if cursor:
            cursor.close()
        if conn: # Aggiunta per evitare errori se la connessione non è mai stata stabilita
            conn.close()


#Endpoint per la modifica prestiti
@app.route('/gestisci_prestiti/<int:id>/update', methods=['POST'])
@login_required
def modifica_prestito(id):
    conn, cursor = db.connection_establish()
    if not conn:
        return jsonify({"msg": "Errore di connessione al database"}), 500

    try:
        # Recupera i dati dal form
        id_libro = request.form['id_libro']
        data_prestito = request.form['data_prestito']
        data_restituzione = request.form['data_restituzione']

        # Controlla che la data di restituzione sia maggiore o uguale alla data di prestito
        if data_restituzione and data_restituzione < data_prestito:
            return jsonify({"msg": "La data di restituzione deve essere successiva alla data di prestito"}), 400

        # Aggiorna il prestito con l'ID specificato
        cursor.execute("""
            UPDATE prestiti 
            SET id_libro = %s, 
                data_prestito = %s, 
                data_restituzione = %s
            WHERE id = %s
        """, (id_libro, data_prestito, data_restituzione, id))
        if data_restituzione:
            query = """
                UPDATE catalogo SET disponibile = 1 WHERE id = %s"""
            cursor.execute(query, (id_libro,))
        conn.commit()
        return jsonify({"msg": "Prestito modificato"}), 201

    except Exception as e:
        print(f"Errore del database: {e}")
        return jsonify({"msg": "Errore durante la modifica del prestito"}), 500

    finally:
        conn.close()

# Endpoint per l'eliminazione di un prestito
@app.route('/gestisci_prestiti/<int:id>/delete', methods=['POST'])
@login_required
def elimina_prestito(id):
    conn, cursor = db.connection_establish()
    if not conn:
        return jsonify({"msg": "Errore di connessione al database"}), 500

    try:
        cursor.execute("""SELECT MAX(id) FROM prestiti""")
        max=cursor.fetchone()
        # Elimina il prestito con l'ID specificato
        if max[0]==id:
            cursor.execute("SELECT id_libro FROM prestiti WHERE id=%s",(id,))
            idlibro=cursor.fetchone()
            cursor.execute("DELETE FROM prestiti WHERE id = %s", (id,))
            conn.commit()
            cursor.execute("UPDATE catalogo SET disponibile=1 WHERE id =%s", (idlibro[0],))
            conn.commit()
        else:
            cursor.execute("DELETE FROM prestiti WHERE id = %s", (id,))
            conn.commit()
        return jsonify({"msg": "Prestito eliminato"}), 201

    except Exception as e:
        print(f"Errore del database: {e}")
        return jsonify({"msg": "Errore durante l'eliminazione del prestito"}), 504

    finally:
        conn.close()


@app.route('/download_prestiti_excel')
def download_prestiti_excel():
    data = db.export_prestiti_query()
    if not data:
        return "Errore nel recupero dati", 500
        
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()

    # Stili
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#A9A9A9',
        'border': 1
    })

    cell_format = workbook.add_format({
        'border': 1
    })

    # Headers
    headers = ['ID', 'Libro', 'ISBN', 'Utente', 'Email', 'Data Prestito', 
              'Data Restituzione', 'Data Prevista', 'Stato']
    
    for col, header in enumerate(headers):
        worksheet.write(0, col, header, header_format)

    # Dati
    for row, record in enumerate(data, 1):
        for col, value in enumerate(record):
            worksheet.write(row, col, value, cell_format)

    # Autofit colonne
    for col in range(len(headers)):
        worksheet.set_column(col, col, 20)
    
    workbook.close()
    output.seek(0)
    
    return send_file(
        output,
        as_attachment=True,
        download_name='prestiti.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

# region - CATALOGO
@app.route('/catalogo')
@login_required
def catalogo():
    conn, cursor = db.connection_establish()
    if not conn:
        return jsonify({"msg": "Errore di connessione al database"}), 500

    try:
        query = """
            SELECT 
                c.id AS id_libro,
                c.nome_libro,
                c.autore,
                c.isbn,
                c.genere,
                c.editore, 
                c.anno_pubblicazione,
                c.posizione,
                CASE
                    WHEN EXISTS (
                        SELECT 1
                        FROM prestiti p
                        WHERE p.id_libro = c.id
                          AND p.data_restituzione IS NULL
                    ) THEN 'In prestito'
                    ELSE 'Disponibile'
                END AS disponibilita
            FROM 
                catalogo c;
        """
        cursor.execute(query)
        books = cursor.fetchall()

        # Converti le tuple in dizionari per un accesso più semplice nel template
        books_list = []
        for book in books:
            book_dict = {
                "id_libro": book[0],
                "nome_libro": book[1],
                "autore": book[2],
                "isbn": book[3],
                "genere": book[4],
                "editore": book[5],
                "anno_pubblicazione": book[6],
                "posizione": book[7],
                "disponibilita": book[8],  # Disponibilità calcolata dalla query
            }
            books_list.append(book_dict)

        return render_template('catalogo.html', books=books_list)

    except Exception as e:
        print(f"Errore del database: {e}")
        return jsonify({"msg": "Errore durante il recupero dei dati"}), 500

    finally:
        conn.close()
    
#region DASHBOARD
@app.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    # Recupera l'identità dell'utente dal token (l'email in questo caso)
    return render_template('dashboard.html')

#Endpoint per la modifica di un libro

@app.route('/modifica_libro/<int:id>/', methods=['POST'])
@login_required
def modifica_libro(id):
    conn, cursor = db.connection_establish()
    if not conn:
        return jsonify({"msg": "Errore di connessione al database"}), 500

    try:
        # Recupera i dati dal form
        nome_libro = request.form['nome_libro']
        autore = request.form['autore']
        isbn = request.form['isbn'].strip()
        genere = request.form['genere']
        editore = request.form['editore']
        anno_pubblicazione = request.form['anno_pubblicazione']
        posizione = request.form['posizione']

        # Aggiorna il libro con l'ID specificato
        cursor.execute("""
            UPDATE catalogo 
            SET nome_libro = %s,
                autore = %s,
                isbn = %s,
                genere = %s,
                editore = %s,
                anno_pubblicazione = %s,
                posizione = %s
            WHERE id = %s
        """, (nome_libro, autore, isbn, genere, editore, anno_pubblicazione, posizione,id))
        conn.commit()
        msg = "Libro aggiornato con successo"
        return jsonify({"success" : True, "msg" : msg}), 201  

    except Exception as e:
        print(f"Errore del database: {e}")
        return jsonify({"msg": "Errore durante l'aggiornamento del libro"}), 500

    finally:
        conn.close()

#Endpoint per l'eliminazione di un libro
@app.route('/libro/delete/<int:id>', methods=['POST'])
@login_required
def elimina_libro(id):
    try:
        connection, cursor = db.connection_establish()
        cursor.execute("DELETE FROM catalogo WHERE id = ?", (id,))
        connection.commit()
        return redirect(url_for('catalogo'))
    finally:
        db.connection_close(connection, cursor)

#region UTENTI
# Endpoint per la registrazione utente lato dashboard
@app.route('/nuovo_utente', methods=['GET', 'POST'])
@login_required
def nuovo_utente():
    if request.method == 'POST':
        email = request.form['email'].strip()
        codice_fiscale = request.form['codice_fiscale'].upper().strip()
        nome_cognome = request.form['nome_cognome']
        numero_telefono = request.form['numero_telefono'].strip()
        

        conn, cursor = db.connection_establish()
        if not conn:
            return jsonify({"msg": "Errore di connessione al database"}), 500

        try:
            # Verifica se l'email esiste già
            cursor.execute("SELECT id FROM utenti WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({"success": False,"msg": "Email già in uso"}), 400
            cursor.execute("SELECT id FROM utenti WHERE codice_fiscale = %s", (codice_fiscale,))
            if cursor.fetchone():
                return jsonify({"success": False,"msg": "Codice fiscale già presente nel database"}), 400

            # Inserisci l'utente nel database
            query = """
                INSERT INTO utenti (email, codice_fiscale, nome_cognome, telefono)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(query, (email, codice_fiscale, nome_cognome, numero_telefono))
            conn.commit()

            # Restituisci un messaggio di successo
            msg = "Utente creato con successo"
            return jsonify({"success": True,'msg': msg}), 201

        except Exception as e:
            print(f"Errore del database: {e}")
            msg = "Errore durante la registrazione"
            return jsonify({"success": False,'msg': msg}), 500

        finally:
            conn.close()
    try:
        conn, cursor = db.connection_establish()
        if not conn:
            return jsonify({"msg": "Errore di connessione al database"}), 500
        cursor.execute("SELECT id, codice_fiscale, nome_cognome, email, telefono FROM utenti")
        utenti = cursor.fetchall()
        return render_template('nuovo_utente.html', utenti=utenti)
    except Exception as e:
        print(f"Errore del database: {e}")
        return jsonify({"msg": "Errore durante il recupero dei dati"}), 500
    finally:
        conn.close()

#Endpoint per la modifica di un utente
@app.route('/modifica_utente/<int:id>', methods=['POST'])
@login_required
def modifica_utente(id):
    email = request.form['email'].strip()
    codice_fiscale = request.form['codice_fiscale'].upper().strip()
    nome_cognome = request.form['nome_cognome']
    numero_telefono = request.form['numero_telefono'].strip()

    conn, cursor = db.connection_establish()
    if not conn:
        return jsonify({"success": False, "msg": "Errore di connessione al database"}), 500

    try:
        # Verifica email duplicata escludendo l'utente corrente
        cursor.execute("SELECT id FROM utenti WHERE email = %s AND id != %s", (email, id))
        if cursor.fetchone():
            return jsonify({"success": False, "msg": "Email già in uso"}), 400

        # Verifica codice fiscale duplicato escludendo l'utente corrente
        cursor.execute("SELECT id FROM utenti WHERE codice_fiscale = %s AND id != %s", (codice_fiscale, id))
        if cursor.fetchone():
            return jsonify({"success": False, "msg": "Codice fiscale già presente nel database"}), 400

        # Aggiorna i dati dell'utente
        query = """
            UPDATE utenti 
            SET email = %s, codice_fiscale = %s, nome_cognome = %s, telefono = %s
            WHERE id = %s
        """
        cursor.execute(query, (email, codice_fiscale, nome_cognome, numero_telefono, id))
        conn.commit()

        return jsonify({"success": True, "msg": "Utente modificato con successo"}), 200

    except Exception as e:
        print(f"Errore del database: {e}")
        return jsonify({"success": False, "msg": "Errore durante la modifica"}), 500

    finally:
        conn.close()
        
        
#Endpoint per l'elimina_utente
@app.route('/elimina_utente/<int:id>', methods=['POST'])
@login_required
def elimina_utente(id):
    try:
        connection, cursor = db.connection_establish()
        cursor.execute("DELETE FROM utenti WHERE id = ?", (id,))
        connection.commit()
        return jsonify({"success": True, "msg": "Utente eliminato con successo"}), 200
    except Exception as e:
        if "foreign key constraint fails" in str(e):
            return jsonify({"success": False, "msg": "Impossibile eliminare l'utente perche' ha prestiti registrati"}), 400
        else:
            print(f"Errore inatteso durante l'eliminazione utente: {e}") # Log dell'errore per debug
            return jsonify({"success": False, "msg": "Errore durante l'eliminazione dell'utente"}), 500
    finally:
        db.connection_close(connection, cursor)
         
#endregion



if __name__ == '__main__':
    app.run(ssl_context = ('cert.pem', 'key.pem'), debug=True)
