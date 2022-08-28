import socket
import local_vars # oma email ja salasana

# stunnel ip ja port
HOST = "127.0.0.1"
PORT = 143

"""
Oma email ja salasana erillisestä tiedostosta, jota ei ole
laitettu githubiin.

Huom. IMAP Gmail ei toimi Google-tilin salasanalla, vaan sitä varten
tarvitsee luoda erillinen 'app password'. Salasana ei saa olla sama kuin
POP3:a varten.
App passwords: https://support.google.com/accounts/answer/185833?hl=en

Testatut komennot:
>login
>f fetch 1:5 (BODY[HEADER.FIELDS (SUBJECT DATE FROM)])  # otsikko, pvm, lähettäjä
>f fetch 1 BODY[1.1]    # BODY[1.1] palauttaa viestin sisällön muodossa text/plain
>logout
"""
with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.connect((HOST, PORT))
    state = 'AUTH'
    print("End session at any time by typing 'logout'")

    while True:
        data = s.recv(1024)
        data = data.decode("utf-8")
        print(data)
        
        if state == 'AUTH':
            if "Gimap ready" in data:
                print ('Connected')
                # login: lähetetään käyttäjän email ja salasana
                email = local_vars.EMAIL
                pw = local_vars.PASSWORD
                cmd = f"a1 login {email} {pw}\r\n"
                s.sendall(cmd.encode("utf-8"))

            if 'a1 OK' in data:
                print('login successful')
                state = 'EXAMINE'
                cmd = "e1 EXAMINE INBOX\r\n"
                # valitaan tässä aina inbox, ei roskakoria tai mitään muuta            
                s.sendall(cmd.encode("utf-8"))

        # EXAMINE on read-only, niin ei vahingossakaan tehdä muutoksia
        elif state == 'EXAMINE':
            if "e1 OK" in data:                
                state = 'BROWSE'
                # listataan selkeyden vuoksi vain viiden vanhimman sähköpostin otsikko, pvm, lähettäjä
                cmd = "f1 fetch 2:5 (BODY[HEADER.FIELDS (SUBJECT DATE FROM)])\r\n"
                s.sendall(cmd.encode("utf-8"))

        elif state == 'BROWSE':
            if "f1 OK" in data:
                while True:
                    try:
                        print("Input a number between 1 and 5 to choose message to be displayed.")
                        i = input()
                        if i.lower() == 'logout':
                            i = "a2 logout\r\n"
                            s.sendall(i.encode("utf-8"))
                            print("Ending session.")
                            break            
                        num = int(i)
                        if num < 6 and num > 0:
                            break
                    except:
                        # syötetty jotain muuta kuin kokonaisluku
                        pass
                    
                cmd = f"f2 fetch {str(num)} BODY[1.1]\r\n"
                s.sendall(cmd.encode('utf-8'))

            if "f2 OK" in data:
                print("Choose another message or logout by typing 'logout'")
                i = input()
                while not int(i) or int(i) >5 or int(i) < 1:
                    print("Input a number between 1 and 5.")
                    i = input()
                    if i.lower() == 'logout':
                        i = "a2 logout\r\n"
                        s.sendall(i.encode("utf-8"))
                        print("Ending session.")
                # en saanut selvitettyä, miten saisin pelkän tekstin ilman viestin liitteitä tai html:ää
                s.sendall(f"f2 fetch {i} BODY[1]\r\n".encode("utf-8"))

            if "f2 NO" in data:
                print("Something went wrong. Try another message.")
                i = input()
                while not int(i) or int(i) >5 or int(i) < 1:                    
                    i = input()
                    if i.lower() == 'logout':
                        i = "a2 logout\r\n"
                        s.sendall(i.encode("utf-8"))
                        print("Ending session.")
                s.sendall(f"f2 fetch {i} BODY[1.1]\r\n".encode("utf-8"))

        elif data.startswith('* BAD'):
            # jos näin rajallisilla toiminnoilla on mennyt näin pahasti mennyt pieleen, 
            # ei ole mielekästä jatkaa sessiota
            print("An error occurred, terminating session.")
            s.sendall("a2 logout\r\n".encode("utf-8"))
            break
        
        # RFC 3501 3.4 Logout State
        # "...the client MUST read the tagged OK response to the LOGOUT command before
        # the client closes the connection."
        elif "a2 OK" in data:
            break

        else:
            print('pass')
            pass
