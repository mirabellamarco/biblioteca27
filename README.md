Sviluppato con Gabriele Musmeci, tra momenti di pura ispirazione e altri di completo sconforto. But hey, it works!(https://github.com/gabrielemusmecidev)



SETUP:

Creare un file .env nella main directory con i seguenti parametri:

  `DB_USER=`
	
  `DB_PASSWORD=`
	
  `EMAIL_USERNAME=`
	
  `EMAIL_PASSWORD=`
	
  `JWT_SECRET_KEY=`
	
  `FLASK_SECRET_KEY=`


  Per abilitare reminder_sender.py:
   - configurare i parametri SMTP SSL con i settaggi della propria mail in reminder_sender.py alla riga `with smtplib.SMTP_SSL("address", port) as server:`
