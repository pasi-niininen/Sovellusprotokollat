from distutils.log import error
import socket
import re

HOST = "127.0.0.1"
PORT = 12345

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
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen()
    error_msg = b'500 Syntax error\r\n'
    cmd = ""
    email_msg = ""
    while (True):
        conn, addr = s.accept()
        with conn:
            print(f"Connected by {addr}")
            conn.sendall(b'220 Connection established\r\n')
            state = 'helo'
            recipients = []
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
                            cmd = ""
                            # regex tarkistaa merkkijonon muodon, niin melko turvallisesti voi
                            # ottaa emailin sulkeiden välistä indeksejä käyttämällä
                            email = cmd[9:-3] 
                            recipients.append(email)
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
                            conn.sendall(b'250 OK\r\n')
                            cmd = ""
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