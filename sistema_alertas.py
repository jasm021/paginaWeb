from flask import Flask, render_template, request, jsonify
import csv
import time

app = Flask(__name__)


# 1. NORMALIZACIÓN
def normalizar_texto(texto):
    texto = texto.lower()
    reemplazos = {'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u', 'ü': 'u'}
    for original, nuevo in reemplazos.items():
        texto = texto.replace(original, nuevo)
    signos = [',', '.', ';', ':', '¡', '!', '¿', '?', '"', '(', ')', '-', '_']
    for signo in signos:
        texto = texto.replace(signo, ' ')
    return " ".join(texto.split())

def funcion_falla(P):
    m = len(P)
    valor_f = [0] * m
    k = 0
    j = 1
    while j < m:
        if P[j] == P[k]:
            valor_f[j] = k + 1
            j += 1
            k += 1
        elif k > 0:
            k = valor_f[k - 1]
        else:
            j += 1
    return valor_f
# 2. KMP
def find_kmp(T, P):
    n, m = len(T), len(P)
    posiciones = []
    comparaciones = 0
    if m == 0 or m > n: return posiciones, comparaciones
    result_failure = funcion_falla(P)
    j, k = 0, 0
    while j < n:
        comparaciones += 1
        if T[j] == P[k]:
            if k == m - 1:
                posiciones.append(j - m + 1)
                k = result_failure[k - 1] if k > 0 else 0
            else:
                j += 1
                k += 1
        elif k > 0:
            k = result_failure[k - 1]
        else:
            j += 1
    return posiciones, comparaciones

# 3. BOYER MOORE
def find_boyer_moore(T, P):
    n, m = len(T), len(P)
    posiciones = []
    comparaciones = 0
    if m == 0 or m > n: return posiciones, comparaciones
    last = {}
    for k in range(m):
        last[P[k]] = k
    i, k = m - 1, m - 1
    while i < n:
        comparaciones += 1
        if T[i] == P[k]:
            if k == 0:
                posiciones.append(i)
                i += m
                k = m - 1
            else:
                i -= 1
                k -= 1
        else:
            j = last.get(T[i], -1)
            i += m - min(k, j + 1)
            k = m - 1
    return posiciones, comparaciones


# 4. RUTAS DE FLASK Y API
def cargar_datos():
    patrones = []
    mensajes = []
    try:
        with open('patrones_alerta_estudiantil.csv', mode='r', encoding='utf-8') as f:
            lector = csv.DictReader(f)
            for fila in lector:
                patrones.append({
                    'patron': fila['Patron'],
                    'categoria': fila['Categoria'],
                    'nivel': fila['Nivel_Alerta'],
                    'sugerencia': fila['Sugerencia']
                })
    except FileNotFoundError:
        pass

    try:
        with open('mensajes.txt', mode='r', encoding='utf-8') as f:
            lineas = [linea.strip() for linea in f if linea.strip()]
            fuentes = ['Foro Virtual', 'Tutoría', 'Encuesta Bienestar', 'Mensaje Docente']
            for i, texto in enumerate(lineas):
                mensajes.append({
                    'id': f"m{i+1}",
                    'text': texto,
                    'source': fuentes[i % 4]
                })
    except FileNotFoundError:
        pass
    
    return patrones, mensajes

@app.route('/')
def index():
    patrones, mensajes = cargar_datos()
    return render_template('index.html', patrones_json=patrones, mensajes_json=mensajes)

@app.route('/api/ejecutar', methods=['POST'])
def ejecutar():
    datos = request.json
    algoritmo_seleccionado = datos.get('algo', 'both')
    usar_normalizacion = datos.get('useNorm', True)
    
    patrones, mensajes = cargar_datos()
    resultados = []
    
    for idx, msg_obj in enumerate(mensajes):
        texto_original = msg_obj['text']
        texto_procesar = normalizar_texto(texto_original) if usar_normalizacion else texto_original.lower()
        
        detectado = False
        kmp_comp_final, bm_comp_final = 0, 0
        
        for pat in patrones:
            pat_procesar = normalizar_texto(pat['patron']) if usar_normalizacion else pat['patron'].lower()
            
            posiciones, kmpComp, bmComp, tKmp, tBm = [], 0, 0, 0, 0
            
            if algoritmo_seleccionado in ['kmp', 'both']:
                t0 = time.perf_counter()
                res_kmp, kmpComp = find_kmp(texto_procesar, pat_procesar)
                tKmp = (time.perf_counter() - t0) * 1000
                posiciones = res_kmp
                
            if algoritmo_seleccionado in ['bm', 'both']:
                t1 = time.perf_counter()
                res_bm, bmComp = find_boyer_moore(texto_procesar, pat_procesar)
                tBm = (time.perf_counter() - t1) * 1000
                if not posiciones: 
                    posiciones = res_bm
            
            if posiciones:
                detectado = True
                resultados.append({
                    'id': idx + 1, 'mensaje': texto_original, 'source': msg_obj['source'],
                    'posiciones': posiciones, 'kmpComp': kmpComp, 'bmComp': bmComp, 
                    'kmpTime': tKmp, 'bmTime': tBm, 'categoria': pat['categoria'], 
                    'nivel': pat['nivel'], 'sugerencia': pat['sugerencia'],
                    'patron': pat['patron'], 'detected': True
                })
                break
            else:
                kmp_comp_final, bm_comp_final = kmpComp, bmComp
                
        if not detectado:
            resultados.append({
                'id': idx + 1, 'mensaje': texto_original, 'source': msg_obj['source'],
                'posiciones': [], 'kmpComp': kmp_comp_final, 'bmComp': bm_comp_final, 
                'kmpTime': 0, 'bmTime': 0, 'categoria': 'Sin Alerta', 'nivel': 'Ninguno', 
                'sugerencia': 'No requiere acción', 'patron': '', 'detected': False
            })

    return jsonify({'resultados': resultados})

if __name__ == '__main__':
    app.run(debug=True)