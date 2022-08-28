import sys
from logging import exception
import socket
import re

HOST = "127.0.0.1"
SMTP_PORT = 12345
POP3_PORT = 110
inbox = []

"""
Testattu manuaalisesti telnetillä ja omalla clientillä komennoilla:
>user testuser@example.com
>pass this is a password
>list
>invalid command
>quit
"""
def listen_pop3(s):
    try:
        s.settimeout(5)
        s.listen()
        conn, addr = s.accept()
        with conn:            
            state = 'AUTH'
            user_input = ""
            user = None
            pw = None
            conn.sendall(b'+OK POP3 server ready\r\n')
            while True:
                data = (conn.recv(1024)).decode('utf-8')
                user_input += data

                if user_input.lower() == "quit\r\n":
                    if state == 'AUTH':
                        # asiakas keskeyttänyt autentikoinnin, ei tehdä mitään
                        pass
                    else:                        
                        state = 'UPDATE'
                        # vasta tässä poistettaisiin mitään postilaatikosta
                    conn.sendall(b'+OK Goodbye\r\n')
                    break

                if state == 'AUTH':                    
                    if len(user_input) >= 2 and user_input[-2:] == "\r\n":                        
                        if user is None:
                            x = re.search("user .+@.+\\..+\r\n", user_input, re.IGNORECASE)
                            if x:
                                conn.sendall(b'+OK send PASS\r\n')
                                print(user_input)
                                user = user_input[:-2]
                                user_input = ""
                            else:
                                conn.sendall(b'-ERR [AUTH] Username and password not accepted.\r\n')
                                break
                        else:
                            x = re.search("pass .+\r\n", user_input, re.IGNORECASE)
                            if x:
                                print(f"password: {user_input}")
                                conn.sendall(b'+OK Welcome.\r\n')
                                pw = user_input[:-2]
                                user_input = ""
                                state = 'TRANS'
                                
                            else:
                                conn.sendall(b'-ERR [AUTH] Username and password not accepted.\r\n')
                                break

                if state == 'TRANS':
                    if len(user_input) >= 2 and user_input[-2:] == "\r\n":
                        print(user_input)
                        if user_input == 'list\r\n':
                            user_input = ""
                            msg_list = ""
                            inbox_size = 0
                            i = 0
                            for email in inbox:
                                i = i+1
                                email_size = sys.getsizeof(email)
                                inbox_size = inbox_size+email_size
                                msg_list += f"{i} {email_size}\r\n"
                            if i == 0:
                                msg_list = "+OK no messages\r\n"
                            else:
                                # alkuun viestien kokonaismäärä ja loppuun lopetusmerkki
                                msg_list = f"+OK {i} messages ({inbox_size} bytes)\r\n" + msg_list + ".\r\n"
                            conn.sendall(msg_list.encode('utf-8'))
                        else:
                            user_input = ""
                            conn.sendall(b'-ERR Command not understood\r\n')

    except Exception:
        # jos viiden sekunnin aikana ei tule asiakasyhteyttä, siirrytään
        # kuuntelemaan toista porttia
        print("pop3 timeout")
        pass
    return


"""
Vain yksi yhteys auki kerrallaan. Jos asiakkaita on useampi, ne joutuvat 
jonottamaan kunnes nykyinen yhteys suljetaan.

Jos missään tilassa (HELO, MAIL FROM, RCPT TO, DATA, QUIT) tulee asiakkaalta
virheellinen käsky tai parametri, palautetaan virhe "500 Syntax error" ja
suljetaan yhteys.

Bugeja:
- Jos on avoin yhteys asiakkaaseen, Ctrl+C näppäinyhdistelmällä palvelin sulkeutuu
vasta sen jälkeen, kun asiakas yrittää lähettää viestin tai sulkee yhteyden.
- Jos ei ole avointa yhteyttä, Ctrl+C näppäinyhdistelmällä palvelin sulkeutuu
vasta sen jälkeen, kun asiakas yrittää muodostaa yhteyden
(tai komentorivi suljetaan).
- Jos tekee näppäilyvirheen telnetillä, koko rivi pitää pyyhkiä pois backspacella ja
aloittaa komento alusta asti uudestaan.
- Jos sulkee terminaalin, jossa telnetillä on avoin yhteys palvelimeen, palvelin ei
poistu silmukasta, vaan sen joutuu käynnistämään uudelleen
- Ääkköset eivät tomi, vaan niiden käyttö johtaa poikkeukseen

Testattu manuaalisesti telnetillä tähän tapaan tapaan:
>telnet localhost 12345
S: 220 Connection established
C: HELO jyu.fi
S: 250 OK
C: MAIL FROM:<aaa@aaa.aaa>
S: 250 OK
C: RCPT TO:<bbb@bbb.bbb>
S: 250 OK
C: RCPT TO:<ccc@ccc.ccc>
S: 250 OK
C: DATA
S: 354 End data with <CR><LF>.<CR><LF>
C: this
   is
   a
   test.
   .

S: 250 OK
C: QUIT
S: 221 Bye
"""
def listen_smtp(s):
    try:
        s.settimeout(5)
        s.listen()
        error_msg = b'500 Syntax error\r\n'
        cmd = ""
        email_msg = ""        
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            conn.sendall(b'220 Connection established\r\n')
            state = 'helo'
            recipients = []
            sender = ""
            while True:
                data = (conn.recv(1024)).decode('utf-8')
                if state != "data":
                    # eli otetaan vastaan komentoa, ei viestin sisältöä
                    cmd += data
                
                print(cmd)                

                # VIESTIN SISÄLTÖ
                if state == 'data':
                    email_msg += data
                    # tarkistetaan, päättyykö viesti oikealla tavalla
                    if len(email_msg) >= 5 and email_msg[-5:] == "\r\n.\r\n":
                        print(email_msg)
                        conn.sendall(b'250 OK\r\n')
                        email = {
                            "sender": sender,
                            "recipients": recipients,
                            "content": email_msg[:-5]
                        }
                        inbox.append(email)
                        print(inbox)
                        cmd = ""
                        email_msg = ""
                        state = 'quit'
                        # tämän jälkeen tulisi odottaa lähetyksen onnistumista
                        # tässä kuitenkin vastataan heti 250 OK viestillä                        
                
                # VIESTIN VASTAANOTTAJAT
                elif state == 'rcpt':
                    if len(cmd) >= 2 and cmd[-2:] == "\r\n":
                        x = re.search("RCPT TO:<.+@.+\\..+>\r\n", cmd, re.IGNORECASE)                        
                        if x:
                            conn.sendall(b'250 OK\r\n')
                            # regex tarkistaa merkkijonon muodon, niin melko turvallisesti voi
                            # ottaa emailin sulkeiden välistä indeksejä käyttämällä
                            email = cmd[9:-3]
                            recipients.append(email)
                            cmd = ""
                        elif cmd.lower() == 'data\r\n':
                            # voi olla useampi vastaanottaja, joten lisätään niitä kunnes
                            # saadaan DATA-komento
                            conn.sendall(b'354 End data with <CR><LF>.<CR><LF>\r\n')
                            cmd = ""
                            state = 'data'
                        else:
                            conn.sendall(error_msg)
                            cmd = ""
                            break
                
                # VIESTIN LÄHETTÄJÄ
                elif state == 'mail':
                    if len(cmd) >= 2 and cmd[-2:] == "\r\n":
                        x = re.search("MAIL FROM:<.+@.+\\..+>\r\n", cmd, re.IGNORECASE)
                        if x:
                            sender = cmd[11:-3]
                            cmd = ""
                            conn.sendall(b'250 OK\r\n')
                            state = 'rcpt'
                        else:
                            conn.sendall(error_msg)
                            cmd = ""
                            break

                # DOMAIN
                elif state == 'helo':                    
                    if len(cmd) >= 2 and cmd[-2:] == "\r\n":
                        x = re.search("HELO .+\\..+\r\n", cmd, re.IGNORECASE)
                        if x:
                            conn.sendall(b'250 OK\r\n')
                            cmd = ""
                            state = 'mail'                            
                        else:
                            conn.sendall(error_msg)
                            cmd = ""
                            break

                # LOPETUSVIESTI
                elif state == 'quit':
                    if len(cmd) >= 2 and cmd[-2:] == "\r\n":
                        if cmd.lower() == 'quit\r\n':
                            conn.sendall(b'221 Bye\r\n')
                            cmd = ""
                            break
                        else:
                            conn.sendall(error_msg)
                            cmd = ""
                            break

                else:
                    print("jotain meni pieleen...")
                    email_msg = ""
                    cmd = ""
                    break
    except Exception:
        # jos viiden sekunnin aikana ei tule asiakasyhteyttä, siirrytään
        # kuuntelemaan toista porttia
        print("smtp timeout")
        pass
    return


socket_smtp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
socket_pop3 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

socket_smtp.bind((HOST, SMTP_PORT))
socket_pop3.bind((HOST, POP3_PORT))

# Kuunnellaan vain yhtä porttia kerrallaan vuorotellen.
s = 1
while True:
    if s == 1:
        listen_smtp(socket_smtp)
        s = 2
    else:
        listen_pop3(socket_pop3)
        s = 1