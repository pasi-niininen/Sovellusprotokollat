import socket
import local_vars # oma email ja salasana

# stunnel (tai oma palvelin) ip ja port
HOST = "127.0.0.1"
PORT = 110

"""
Testattu Gmailia ja omaa SMTP-palvelinta samalla tapaa.
Oma email ja salasana erillisestä tiedostosta, jota ei ole
laitettu githubiin.

Huom. pop3 Gmail ei toimi Google-tilin salasanalla, vaan sitä varten
tarvitsee luoda erillinen 'app password'. Salasana ei saa olla sama kuin
IMAP:ia varten.
App passwords: https://support.google.com/accounts/answer/185833?hl=en

Testatut komennot:
>user xxx@gmail.com
>pass xxxxxxxxxxxxx
>list
>quit
"""
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    while True:
        data = s.recv(1024)
        data = data.decode("utf-8")
        print(data)
        
        if "+OK" in data:
            if "ready" in data:
                # lähetetään käyttäjän email
                email = local_vars.EMAIL
                email += "\r\n"
                s.sendall(f"user {email}".encode("utf-8"))

            elif data == "+OK send PASS\r\n":
                # lähetetään käyttäjän salasana
                pw = local_vars.PASSWORD
                pw += "\r\n"
                s.sendall(f"pass {pw}".encode("utf-8"))

            elif data == "+OK Welcome.\r\n" or "messages" in data:
                # käyttäjä voi valita seuraavan komennon
                print("Type 'list' to list all emails. Type 'quit' to end the session.")
                i = input()
                while (i.lower() != 'list' and i.lower() != 'quit') or (i.lower() != 'quit' and i.lower() != 'list'):
                    print("Invalid command.")
                    i = input()
                if i.lower() == 'list':
                    i += "\r\n"
                    s.sendall(i.encode("utf-8"))
                elif i.lower() == 'quit':
                    i += "\r\n"
                    s.sendall(i.encode("utf-8"))
                    print("Ending session.")
                    break

        elif "-ERR" in data:
            print("An error occurred:")
            print(data)
            print("Attempt a manual command or type 'quit' to end the session.")
            i = input()
            i += "\r\n"
            s.sendall(i.encode("utf-8"))

        else:
            # palvelin ei seuraa POP3 protokollaa jos viesti ei ala +OK tai -ERR
            pass
