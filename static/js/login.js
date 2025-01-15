document.addEventListener('DOMContentLoaded', () => { //Carica il DOM
    const loginForm = document.querySelector('form'); //Si prende il form da dove pescare l'errore (da HTML)
    const errorMessage = document.getElementById('login-error'); //Si prende l'id di dove mettere il testo (da HTML)
    const invalidEmail = document.getElementById('invalid-email');
    loginForm.addEventListener('submit', async (Event) => {
        Event.preventDefault(); //Previene il comportamento di default
        errorMessage.textContent = "" //Resetta il messaggio di errore

        const formData = new FormData(loginForm);

        try {
            const response = await fetch('/login', { //Lui si aspetta dall'endpoint /login che torni col metodo POST nel body il contenuto del form (da HTML)
                method: 'POST',
                body: formData
            });

            if (response.ok) {
                window.location.href = '/dashboard' //Reindirizzamento in caso positivo
            } else { //In caso negativo, non riceve un post con un body ma un json (definito da app.py)
                const data = await response.json(); //Gli dico che riceverà un json
                if (data.error == 403){ //Se nel json che gli arriva l'errore è il 403
                    invalidEmail.textContent=data.msg; //Utilizzo il div riservato alla mail non valida
                    invalidEmail.style.display="block";
                    invalidEmail.style.color="red";
                }
                else{ //Altrimenti si tratta della mail o password errata
                    errorMessage.textContent = data.msg; //Come errore imposta quello che riceve da app.py
                    errorMessage.style.display="block" //Roba CSS che definisco dinamicamente
                    errorMessage.style.color='red'; //Roba CSS che definisco dinamicamente
                }
            }
        } catch (error) { //Se non riceve nulla dalla pagina lancia e cattura un'eccezione
            errorMessage.textContent = "Errore di connessione, si prega di riprovare";
            error.style.display="block"
            errorMessage.style.color='red';
        }
    });
});