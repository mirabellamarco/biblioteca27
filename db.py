import mariadb
import os
from dotenv import load_dotenv
from mariadb import Error
from prettytable import PrettyTable
from flask_bcrypt import Bcrypt
bcrypt = Bcrypt()

# ESEGUIRE in cmd 'pip install -r requirements.txt' PER ESEGUIRE IL CODICE

#region CONNESSIONE
load_dotenv() #recupero sicuro delle credenziali da file.env

def connection_establish():
    """
    Funzione per stabilire una connessione al database.
    """
    connection = mariadb.connect(
        host="localhost",
        user=os.getenv("DB_USER"), 
        password=os.getenv("DB_PASSWORD"),
        database="biblioteca27"
    )
    cursor = connection.cursor()
    return connection, cursor

def connection_close(connection, cursor):
    """
    Funzione per chiudere la connessione al database.
    """
    if cursor:
        cursor.close()
    if connection:
        connection.close()

#endregion

#region MK.DATABASE
def first_connection():
    """
    Funzione per stabilire la prima connessione a MariaDB.
    """
    connection = mariadb.connect(
        host="localhost",
        user=os.getenv("DB_USER"), 
        password=os.getenv("DB_PASSWORD")
    )
    cursor = connection.cursor()
    return connection, cursor
        
def create_db():
    """
    Funzione per creare il database biblioteca27.
    """
    connection = None
    cursor = None
    try:
        connection, cursor = first_connection()
        cursor = connection.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS biblioteca27;")
        print("Database creato con successo o già esistente\n")
    except Error as e:
        print(f"Errore durante la connessione a MariaDB o durante la creazione del database: {e}")
    finally:
        connection_close(connection, cursor)

def create_table_catalogo():
    """
    Funzione per creare la tabella Libri nel database biblioteca27.
    """
    try:
        connection, cursor = connection_establish()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS catalogo (
            id BIGINT PRIMARY KEY AUTO_INCREMENT,
            nome_libro VARCHAR(255) NOT NULL,
            autore VARCHAR(255) NOT NULL,
            isbn VARCHAR(17)NOT NULL UNIQUE,
            genere VARCHAR(100),
            editore VARCHAR(255),
            anno_pubblicazione SMALLINT(4),
            posizione VARCHAR(50),
            disponibile TINYINT(1) DEFAULT 1
        );
        """
        cursor.execute(create_table_query)
        print("Tabella Catalogo creata o già esistente.\n")
    except Error as e:
        print(f"Errore durante la creazione della tabella: {e}\n")
    finally:
        connection_close(connection, cursor)

def create_table_utenti():
    """
    Funzione per creare la tabella utenti nel database biblioteca27.
    """
    try:
        connection, cursor = connection_establish()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS utenti (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            codice_fiscale VARCHAR(21) NOT NULL UNIQUE,
            admin BOOLEAN DEFAULT FALSE,
            password VARCHAR(255) NOT NULL DEFAULT '',
            nome_cognome VARCHAR(50) NOT NULL,
            email VARCHAR(50) NOT NULL UNIQUE,
            telefono BIGINT
        );
        """
        cursor.execute(create_table_query)
        print("Tabella Utenti creata o già esistente.\n")
    except Error as e:
        print(f"Errore durante la creazione della tabella: {e}")
    finally:
        connection_close(connection, cursor)
        
def stampa_query(cursor):
        table = PrettyTable() #formattazione tabella per stampa
        table.field_names = [desc[0] for desc in cursor.description] #recupera i nomi delle colonne da cursor
        for row in cursor:
           table.add_row(row)
        print(table)

#endregion

#region INSERT
def insert_table_utenti(user_details):
    """
    Funzione per inserire un utente nella tabella utenti.
    """
    try:
        connection, cursor = connection_establish()
        insert_or_update_query = """
        INSERT INTO utenti (codice_fiscale, admin, password, nome_cognome, email, telefono)
        VALUES (?, ?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE
            codice_fiscale = VALUES(codice_fiscale),
            admin = VALUES(admin),
            password = VALUES(password),
            nome_cognome = VALUES(nome_cognome),
            email = VALUES(email),
            telefono = VALUES(telefono)
        """
        cursor.execute(insert_or_update_query, user_details)
        connection.commit()
        print("-----------------------------------------------")
        print("\n\nUtente inserito o aggiornato con successo.\n")
    except Error as e:
        print(f"Errore durante l'inserimento o l'aggiornamento: {e}\n")
    finally:
        connection_close(connection, cursor)

def insert_table_catalogo(book_details):
    """
    Funzione per inserire un libro nella tabella catalogo.
    """
    try:
        connection, cursor = connection_establish()
        insert_or_update_query = """
        INSERT INTO catalogo (nome_libro, autore, isbn, genere, editore, anno_pubblicazione, posizione)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE
            nome_libro = VALUES(nome_libro),
            autore = VALUES(autore),
            genere = VALUES(genere),
            editore = VALUES(editore),
            anno_pubblicazione = VALUES(anno_pubblicazione)
            posizione = VALUES(posizione);
        """
        cursor.execute(insert_or_update_query, book_details)
        connection.commit()
        print("\nLibro inserito o aggiornato con successo.\n")
    except Error as e:
        print(f"Errore durante l'inserimento o l'aggiornamento: {e}")
    finally:
        connection_close(connection, cursor)

#region PRESTITI
def create_table_prestiti():
    """
    Funzione per creare la tabella prestiti nel database biblioteca27.
    """
    try:
        connection, cursor = connection_establish()
        create_table_query = """
        CREATE TABLE IF NOT EXISTS prestiti (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            id_utente BIGINT NOT NULL,
            id_libro BIGINT NOT NULL,
            data_prestito DATE NOT NULL,
            data_restituzione DATE,
            data_restituzione_prevista DATE NOT NULL,
            promemoria_inviato TINYINT(1) DEFAULT 0,
            FOREIGN KEY (id_utente) REFERENCES utenti(id),
            FOREIGN KEY (id_libro) REFERENCES catalogo(id) ON DELETE CASCADE
        );
        """
        cursor.execute(create_table_query)
        print("Tabella Prestiti creata o già esistente.\n")
    except Error as e:
        print(f"Errore durante la creazione della tabella: {e}")
    finally:
        connection_close(connection, cursor)

def insert_table_prestiti(prestito_details):
    """
    Funzione per inserire o aggiornare un prestito nella tabella prestiti.
    """
    try:
        connection, cursor = connection_establish()
        insert_or_update_query = """
        INSERT INTO prestiti (id_utente, id_libro, data_prestito, data_restituzione, data_restituzione_prevista)
        VALUES (?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE
            id_utente = VALUES(id_utente),
            id_libro = VALUES(id_libro),
            data_prestito = VALUES(data_prestito),
            data_restituzione = VALUES(data_restituzione);
        """
        # Verifica se la data di restituzione è fornita
        if len(prestito_details) == 3:
            prestito_details.append(None)  # Aggiungi NULL se manca la data di restituzione
        cursor.execute(insert_or_update_query, prestito_details)
        agg_disp_query = """
        UPDATE catalogo
        SET disponibile = 0
        WHERE id = %s; 
        """
        cursor.execute(agg_disp_query, (prestito_details[1],))
        connection.commit()
        print("\nPrestito inserito o aggiornato con successo.\n")
    except Error as e:
        print(f"Errore durante l'inserimento o l'aggiornamento: {e}")
    finally:
        connection_close(connection, cursor)


#region VISTE 
def vista_prestiti():
    """
    Funzione per visualizzare il catalogo con i dettagli dei prestiti.
    """
    try:
        connection, cursor = connection_establish()
        query = """
        SELECT 
            catalogo.id AS id_libro,
            catalogo.nome_libro,
            catalogo.autore,
            catalogo.isbn,
            catalogo.genere,
            catalogo.editore,
            catalogo.anno_pubblicazione,
            catalogo.posizione,
            prestiti.data_prestito,
            prestiti.data_restituzione
        FROM 
            catalogo
        LEFT JOIN 
            prestiti 
        ON 
            catalogo.id = prestiti.id_libro;
        """
        cursor.execute(query)
        stampa_query(cursor)
    except Error as e:
        print(f"Errore durante la visualizzazione del catalogo: {e}")
    finally:
        connection_close(connection, cursor)

def visualizza_intero_db():
    """
    Funzione per visualizzare tutte le tabelle del database biblioteca27.
    """
    try:
        connection, cursor = connection_establish()
        if not connection or not cursor:
            print("Connessione al database non riuscita.")
            return

        # Recupera i nomi delle tabelle dal database
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        stampa_query(cursor)

        if not tables:
            print("Il database è vuoto.")
            return

        # Stampa i dati di ogni tabella
        for table in tables:
            query = f"SELECT * FROM {table[0]}"
            cursor.execute(query)
            stampa_query(cursor)

    except Error as e:
        print(f"Errore durante la visualizzazione del database: {e}")
    finally:
        connection_close(connection, cursor)

def inserisci_esempi():
    """
    Funzione per popolare il database con libri di esempio
    """
    try:
        connection, cursor = connection_establish()
        insert_or_update_query = """
INSERT INTO catalogo (nome_libro, autore, isbn, genere, editore, anno_pubblicazione, posizione)
VALUES
('Le Avventure di ChatGPT', 'OpenAI Author', '978-12-34567-01-1', 'Fantascienza', 'AI Books Publishing', 2023, 'Scaffale A1'),
('COBOL per Tutti', 'Guido Van Cossum', '978-12-34567-03-3', 'Programmazione', 'TechPress', 2020, 'Scaffale C2'),
('Il Signore degli Stack', 'Tolkien Developer', '978-12-34567-04-4', 'Fantasia', 'Middle Earth Pub', 1954, 'Scaffale D1'),
('Ricette con Pennette', 'Isaac Modder', '978-12-34567-06-6', 'Cucina', 'ModKitchen Books', 2024, 'Scaffale A2'),
('Il Signore del Broadcast', 'J.V.V. Tolkien', '978-12-34567-07-7', 'Narrativa', 'Mondadori', 1990, 'Scaffale A2'),
('Barry Otter e la Pietra Segreta', 'K.J.Bowling', '978-12-34567-09-9', 'Fantasia', 'Azkaban', 2000, 'Scaffale 9 3/4'),
('2001, Odissea nello Sbazio', 'Gnagrn Gnarl', '978-12-34567-11-1', 'Fantascienza', 'GiGi Editore', 2001, 'Scaffale A3'),
('Orgoglio e Pregipython', 'Bane Austin', '978-12-34567-11-2', 'Narrativa', 'Denzel Books', 1968, 'Scaffale 7'),
('Cento anni di Solitude (Skyrim Collection)', 'Elisabetta Piancavallo', '978-12-34567-11-3', 'Romanzo', 'Balcanican', 2005, 'Scaffale 1'),
('La ragazza della motrice','Siderea Beers','978-12-34567-11-4','Narrativa','FCE',2016,'Scaffale XXIII');
"""
        cursor.execute(insert_or_update_query)
        connection.commit()
        print("Database popolato correttamente")
    except Error as e:
        print(f"Errore durante il popolamento del DB: {e}")
    finally:
        connection_close(connection, cursor)

def inserisci_esempi_utenti():
    """
    Funzione per popolare il database con utenti di esempio
    """
    try:
        connection, cursor = connection_establish()
        insert_or_update_query = """
INSERT INTO utenti (codice_fiscale, admin, password, nome_cognome, email, telefono) 
VALUES 
('RSSMRA80A01H501T', 0, 'password', 'Mario Rossi', 'mario.rossi@example.com', 3331234567),
('VRDGPP75B12F205L', 0, 'password', 'Giuseppe Verdi', 'giuseppe.verdi@example.com', 3459876543),
('BNCLSN70C30G839K', 1, '$2b$12$ZKhHmSf2uyUhErKI/c3hw.3ZTu8Vl3A2fmyIr2Z.t.s2iIOAwZY5a', 'root', 'root@root.it', 999),
('CLDNNR68D45A176Z', 0, 'password', 'Andrea Celentano', 'andrea.celentano@example.com', 3471112222),
('FRRLRA82E56H987Y', 0, 'password', 'Laura Ferrari', 'laura.ferrari@example.com', 3384445555),
('GLLMRC90F67L098X', 0, 'password', 'Marco Galli', 'marco.galli@example.com', 3407778888),
('MRZNDR85G78E432W', 0, 'password', 'Andrea Marzi', 'andrea.marzi@example.com', 3310001111),
('RSSFNC72L01F204U', 0, 'password', 'Francesca Russo', 'francesca.russo@example.com', 3346667777),
('STTMRC76M12A980S', 0, 'password', 'Marco Storti', 'marco.storti@example.com', 3495556666),
('FLRSPN74N23H567V', 0, 'password', 'Floriana Spanu', 'floriana.spanu@stevejobs.academy', 987654331),
('PRTRSS88H89C765V', 0, 'password', 'Sara Patrizi', 'sara.patrizi@example.com', 3462223333),
('MRCMRC75M12A885S', 0, 'password', 'Marco Mirabella', 'mmirabella@stevejobs.academy', 123456789);

"""
        cursor.execute(insert_or_update_query)
        connection.commit()
        print("Database popolato correttamente")
    except Error as e:
        print(f"Errore durante il popolamento del DB: {e}")
    finally:
        connection_close(connection, cursor)



#region MAIN
######## MAIN ########
if __name__ == "__main__":
    create_db()
    create_table_catalogo()
    create_table_utenti()
    create_table_prestiti()
    while True:
        print("Seleziona operazione:\n")
        print("1. Inserisci libro\n")
        print("2. Inserisci utente\n")
        print("3. Inserisci/aggiorna prestito\n")
        print("4. Visualizza catalogo con prestiti \n")
        print("5. Visualizza tutto il database\n")
        print("6 Inserisci titoli esempio\n")
        print("7. Inserisci utenti di esempio\n")
        print("0. Esci\n")
        print("--------------------------\n--------------------------\n")
        scelta = input()
        if scelta == "1":
            book_details = input("Inserisci i dettagli del libro (Titolo, autore, isbn (formato 978-12-34567-01-0), genere, editore, anno di pubblicazione, posizione scaffale): ")
            book_details = book_details.split(",")
            insert_table_catalogo(book_details)
        elif scelta == "2":
            codice_fiscale = input("\nInserisci il codice fiscale: ")
            admin = input("\nInserisci 1 se l'utente ha admin, 0 altrimenti: ")
            password = input(str("\nInserisci la password: "))
            hashed_password = bcrypt.generate_password_hash(password=password).decode('utf-8')
            nome_cognome = input("\nInserisci il nome e il cognome: ")
            email = input("\nInserisci l'email: ")
            telefono = input("\nInserisci il telefono: ")
            user_details = [codice_fiscale, admin, hashed_password, nome_cognome, email, telefono]
            insert_table_utenti(user_details)
        elif scelta == "3":
            prestito_details = input("Inserisci i dettagli del prestito (id_utente, id_libro, data_prestito, data_restituzione, data_restituzione_prevista (formato 1970-01-01)): ")
            prestito_details = prestito_details.split(",")
            insert_table_prestiti(prestito_details)
        elif scelta == "4":
            vista_prestiti()
        elif scelta == "5":
            visualizza_intero_db()
        elif scelta == "6":
            inserisci_esempi()
        elif scelta == "7":
            inserisci_esempi_utenti()
        elif scelta == "0":
            print("Programma terminato.")
            break
        else:
            print("Opzione non valida. Per favore, scegli una delle opzioni disponibili.")
