import numpy as np

##### STIMA DEL LIVELLO DI ATTENZIONE #####

def get_AttLev(prev_ebr, ebr, prev_hr, hr, prev_attLev, head_pos):
    if ebr == -1:
        return -1
    
    # Se non ci sono valori precedenti di attLev considero solo la posizione della testa. Se l'utente guarda verso la webcam l'attenzione è alta altrimenti no.
    if prev_attLev == -1:
        if head_pos == 0:
            prev_attLev = 80
        else:
            prev_attLev = 100
    else:
        if head_pos == 0:
            if prev_attLev >= 10:
                prev_attLev = prev_attLev - 10
            else:
                prev_attLev = 0
        
        if head_pos == 1:
            if prev_attLev <= 90:
                prev_attLev = prev_attLev + 10
            else:
                prev_attLev = 100
    
    # Considero ora il valore di ebr. Per valori alti, sopra 20 l'attenzione potrebbe essere in calo.
    if prev_ebr != -1:
        if ebr > 20 and (ebr-prev_ebr) > 0:
            prev_attLev = prev_attLev - 2
        elif ebr <= 20 and (ebr-prev_ebr) <= 0:
            prev_attLev = prev_attLev + 2
    
    # Considero ora le variazioni di hr. Con variazioni superiori a 5 (aumento dell'hr) si ha un aumento dell'attenzione, viceversa si avrà una diminuzione.
    if prev_hr != -1:
        if (hr-prev_hr) > 2:
            prev_attLev = prev_attLev + 2
        elif (hr-prev_hr) < -2:
            prev_attLev = prev_attLev - 2

    if prev_attLev > 100:
        return 100
    elif prev_attLev < 0:
        return 0
    else:
        return prev_attLev
