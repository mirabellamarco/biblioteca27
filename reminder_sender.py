import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import db
import time

#EMAIL DI TEST 
#email = "biblioteca27@virgilio.it"

def controllo_db():
    try:
        connection, cursor = db.connection_establish()
        if not connection or not cursor:
            print("Connesione al database non riuscita")
        cursor.execute("""SELECT id_libro, id_utente FROM prestiti WHERE promemoria_inviato=0 AND DATEDIFF(data_restituzione_prevista,CURRENT_DATE())=5 AND data_restituzione is null""")
        query_avaiable = cursor.fetchall() #fetchall ritorna una lista di tuple
        #print(f"avaiable: {query_avaiable}")
        query_email=[] #Inizializzo la lista
        for tupla in query_avaiable:
            cursor.execute("""SELECT email from utenti WHERE id=%s""",(tupla[1],))
            query_email.append(cursor.fetchone()) #Appendo nella lista il fetch singolo di ogni iterazione
        #print(f"email: {query_email}")


            

        query_corresponding=[] #Inizializzo la lista
        for tupla in query_avaiable:
            cursor.execute("""
                           SELECT isbn, nome_libro 
                           FROM catalogo 
                           WHERE id = %s""", (tupla[0],))
            query_corresponding.append(cursor.fetchone()) #Appendo nella lista il fetch di ogni iterazione
        #print(f"corresponding: {query_corresponding}")
        db.connection_close(connection,cursor)

        final_dict={} #Inizializzo il dict
        for (id_libro, id_utente), email, (isbn,nome_libro) in zip (query_avaiable, query_email, query_corresponding): #Zip serve a creare un unico iterabli di iterable
            key=(id_libro, isbn, nome_libro)
            value=(id_utente, email[0])
            final_dict[key]=value
        #print(final_dict[0][1])

        
        
        return final_dict
    except Exception as e:
        print(f"Errore nella conensione al database: {e}")
        
    
def controllo_db_scadenza():
    try:
#Stesso codice di sopra ma per prendere quelli in scadenza oggi
        connection, cursor = db.connection_establish()
        if not connection or not cursor:
            print("Connesione al database non riuscita")
        cursor.execute("""SELECT id_libro, id_utente FROM prestiti WHERE DATEDIFF(data_restituzione_prevista,CURRENT_DATE())=0 AND data_restituzione is null""")
        query_avaiable_expiring = cursor.fetchall() #fetchall ritorna una lista di tuple
        #print(f"avaiable: {query_avaiable}")
        query_email_expiring=[] #Inizializzo la lista
        for tupla in query_avaiable_expiring:
            cursor.execute("""SELECT email from utenti WHERE id=%s""",(tupla[1],))
            query_email_expiring.append(cursor.fetchone()) #Appendo nella lista il fetch singolo di ogni iterazione
        #print(f"email: {query_email}")


            

        query_corresponding_expiring=[] #Inizializzo la lista
        for tupla in query_avaiable_expiring:
            cursor.execute("""
                           SELECT isbn, nome_libro 
                           FROM catalogo 
                           WHERE id = %s""", (tupla[0],))
            query_corresponding_expiring.append(cursor.fetchone()) #Appendo nella lista il fetch di ogni iterazione
        #print(f"corresponding: {query_corresponding}")
        db.connection_close(connection,cursor)

        final_dict_expiring={} #Inizializzo il dict
        for (id_libro, id_utente), email, (isbn,nome_libro) in zip (query_avaiable_expiring, query_email_expiring, query_corresponding_expiring): #Zip serve a creare un unico iterabli di iterable
            key=(id_libro, isbn, nome_libro)
            value=(id_utente, email[0])
            final_dict_expiring[key]=value

        return final_dict_expiring
    except Exception as e:
        print(f"Errore nella conensione al database: {e}")






def controllo_db_scaduti():
    try:
        #Stesso codice di sopra ma per prendere quelli scaduti
        connection, cursor = db.connection_establish()
        if not connection or not cursor:
            print("Connesione al database non riuscita")
        cursor.execute("""SELECT id_libro, id_utente FROM prestiti WHERE DATEDIFF(data_restituzione_prevista,CURRENT_DATE())<0 AND data_restituzione is null""")
        query_avaiable_expired = cursor.fetchall() #fetchall ritorna una lista di tuple
        #print(f"avaiable: {query_avaiable}")
        query_email_expired=[] #Inizializzo la lista
        for tupla in query_avaiable_expired:
            cursor.execute("""SELECT email from utenti WHERE id=%s""",(tupla[1],))
            query_email_expired.append(cursor.fetchone()) #Appendo nella lista il fetch singolo di ogni iterazione
        #print(f"email: {query_email}")


            

        query_corresponding_expired=[] #Inizializzo la lista
        for tupla in query_avaiable_expired:
            cursor.execute("""
                           SELECT isbn, nome_libro 
                           FROM catalogo 
                           WHERE id = %s""", (tupla[0],))
            query_corresponding_expired.append(cursor.fetchone()) #Appendo nella lista il fetch di ogni iterazione
        #print(f"corresponding: {query_corresponding}")
        db.connection_close(connection,cursor)

        final_dict_expired={} #Inizializzo il dict
        for (id_libro, id_utente), email, (isbn,nome_libro) in zip (query_avaiable_expired, query_email_expired, query_corresponding_expired): #Zip serve a creare un unico iterabli di iterable
            key=(id_libro, isbn, nome_libro)
            value=(id_utente, email[0])
            final_dict_expired[key]=value
        return final_dict_expired
    except Exception as e:
        print(f"Errore nella conensione al database: {e}")

def invia_reminder(final_dict,chiave): 
    
    username = db.os.getenv("EMAIL_USERNAME")
    destinatario = final_dict[chiave][1]
    password =db.os.getenv("EMAIL_PASSWORD")
    
    
 # Creazione del messaggio
    messaggio = MIMEMultipart()
    messaggio['From'] = username
    messaggio['To'] = destinatario
    messaggio['Bcc'] = "biblioteca27@virgilio.it"
    messaggio['Subject'] = f"Promemoria scadenza prestito"

    # Corpo dell'email
    corpo = f"Gentile utente '{final_dict[chiave][1]}',\n il prestito del libro {chiave[2]} con ISBN {chiave[1]} scade tra 5 giorni, ricorda di restituirlo.\n\nGrazie,\nLo staff di biblioteca27"
    messaggio.attach(MIMEText(corpo, 'plain'))

    try:
        # Connessione al server SMTP con SSL
        with smtplib.SMTP_SSL("out.virgilio.it", 465) as server:
            server.login(username, password)
            server.sendmail(username, destinatario, messaggio.as_string())
            print("Email inviata con successo! (reminder)")
            connection, cursor = db.connection_establish()
            cursor.execute("""UPDATE prestiti SET promemoria_inviato=1 WHERE id_libro=%s""",(chiave[0],))
            connection.commit()
            db.connection_close(connection,cursor)
            server.close()
    except smtplib.SMTPAuthenticationError:
        print("Errore di autenticazione SMTP. Controlla username e password.")
    except smtplib.SMTPServerDisconnected:
        print("Il server SMTP ha chiuso la connessione inaspettatamente.")
    except smtplib.SMTPException as e: # Cattura eccezioni SMTP più specifiche
        print(f"Errore SMTP: {e}")
    except Exception as e:
        print(f"Errore durante l'invio dell'email: {e}")
    finally:
        time.sleep(1)



def invia_expiring(final_dict_expiring,chiave):
    
    username = db.os.getenv("EMAIL_USERNAME")
    destinatarioexpiring = final_dict_expiring[chiave][1]
    password =db.os.getenv("EMAIL_PASSWORD")
    
    
 # Creazione del messaggio
    messaggio = MIMEMultipart()
    messaggio['From'] = username
    messaggio['To'] = destinatarioexpiring
    messaggio['Bcc'] = "biblioteca27@virgilio.it"
    messaggio['Subject'] = f"Scadenza prestito libro imminente"

    # Corpo dell'email
    corpo = f"Gentile utente '{final_dict_expiring[chiave][1]}',\nil prestito del libro {chiave[2]} con ISBN {chiave[1]} scade oggi, affrettati a restituire il libro!\n\nGrazie,\nLo staff di biblioteca27."
    messaggio.attach(MIMEText(corpo, 'plain'))

    try:
        # Connessione al server SMTP con SSL
        with smtplib.SMTP_SSL("out.virgilio.it", 465) as server:
            server.login(username, password)
            server.sendmail(username, destinatarioexpiring, messaggio.as_string())
            print("Email inviata con successo! (expiring)")
            server.close()
    
    except smtplib.SMTPAuthenticationError:
        print("Errore di autenticazione SMTP. Controlla username e password.")
    except smtplib.SMTPServerDisconnected:
        print("Il server SMTP ha chiuso la connessione inaspettatamente.")
    except smtplib.SMTPException as e: # Cattura eccezioni SMTP più specifiche
        print(f"Errore SMTP: {e}")
    except Exception as e:
        print(f"Errore durante l'invio dell'email: {e}")
    finally:
        time.sleep(1)



def invia_expired(final_dict_expired,chiave):
    
    username = db.os.getenv("EMAIL_USERNAME")
    destinatarioexpired = final_dict_expired[chiave][1]
    password =db.os.getenv("EMAIL_PASSWORD")
    
    
 # Creazione del messaggio
    messaggio = MIMEMultipart()
    messaggio['From'] = username
    messaggio['To'] = destinatarioexpired
    messaggio['Bcc'] = "biblioteca27@virgilio.it"
    messaggio['Subject'] = f"Prestito libro scaduto"

    # Corpo dell'email
    corpo = f"Gentile utente '{final_dict_expired[chiave][1]}',\n il prestito del libro {chiave[2]} con ISBN {chiave[1]} è scaduto, ti pregiamo di restituire il libro il prima possibile!\n\nGrazie,\nLo staff di biblioteca27."
    messaggio.attach(MIMEText(corpo, 'plain'))

    try:
        # Connessione al server SMTP con SSL
        with smtplib.SMTP_SSL("out.virgilio.it", 465) as server:
            server.login(username, password)
            server.sendmail(username, destinatarioexpired, messaggio.as_string())
            print("Email inviata con successo! (expired)")
            connection, cursor = db.connection_establish()
            cursor.execute("""UPDATE prestiti SET promemoria_inviato=1 WHERE id_libro=%s""",(chiave[0],))
            connection.commit()
            server.close()
    except smtplib.SMTPAuthenticationError:
        print("Errore di autenticazione SMTP. Controlla username e password.")
    except smtplib.SMTPServerDisconnected:
        print("Il server SMTP ha chiuso la connessione inaspettatamente.")
    except smtplib.SMTPException as e: # Cattura eccezioni SMTP più specifiche
        print(f"Errore SMTP: {e}")
    except Exception as e:
        print(f"Errore durante l'invio dell'email: {e}")
    finally:
        time.sleep(1)    



final_dict = controllo_db()
final_dict_expiring = controllo_db_scadenza()
final_dict_expired = controllo_db_scaduti()

for chiave in final_dict:
    invia_reminder(final_dict,chiave)

for chiave in final_dict_expiring:
    invia_expiring(final_dict_expiring,chiave)

for chiave in final_dict_expired:
    invia_expired(final_dict_expired,chiave)