import fastapi
import time
import os
import asyncio
import shutil
import mysql.connector
import bcrypt
import uvicorn
import json
import numpy as np
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

class User(BaseModel):
    username: str
    email: str
    password: str

def connect_db():
    global connection
    try:
        time.sleep(40) # Wait for db to start
        connection = mysql.connector.connect(
            host="mysql",
            user="user",
            password="password",
            database="db"
        )
        print("Conectado Backend a tb", flush=True)
    except Exception as e:
        print("Error:", e)

app = fastapi.FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:8080",
        "http://localhost:8080",
        "http://0.0.0.0:8080"
        ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

@app.get("/test")
def test():
    return {"message": "Servicio Funcionando"}

@app.post("/register")
def register(user: User):
    if not user.username or not user.password or not user.email:
        raise fastapi.HTTPException(status_code=400, detail="Falta nombre de usuario, contraseña o correo electrónico en la solicitud")

    cursor = connection.cursor()
    try:
        password_bytes = user.password.encode("utf-8")
        hashed_pw = bcrypt.hashpw(password_bytes, bcrypt.gensalt(14))
        cursor.execute("INSERT INTO users (username, password, email) VALUES (%s, %s, %s)", (user.username, hashed_pw.decode("utf-8"), user.email))
        connection.commit()
        return {"message": "Usuario registrado correctamente"}
    except mysql.connector.Error as err:
        raise fastapi.HTTPException(status_code=500, detail=f"Error interno del servidor: {err}")
    finally:
        cursor.close()

@app.post("/login")
async def login(request: fastapi.Request):
    data = await request.json()

    username = data.get("username")
    password = data.get("password")

    User.username = username

    if not username or not password:
        raise fastapi.HTTPException(status_code=400, detail="Falta nombre de usuario o contraseña en la solicitud")

    cursor = connection.cursor()
    try:
        cursor.execute("SELECT password, username, email FROM users WHERE username = %s", (username,))
        user_data = cursor.fetchone()
        
        if user_data:
            hashed_pw = user_data[0].encode("utf-8")
            if bcrypt.checkpw(password.encode("utf-8"), hashed_pw):
                return {"message": "Inicio de sesión exitoso", "username": user_data[1], "email": user_data[2]}
            else:
                raise fastapi.HTTPException(status_code=401, detail="Contraseña incorrecta")
        else:
            raise fastapi.HTTPException(status_code=404, detail="Usuario no encontrado")
    except mysql.connector.Error as err:
        raise fastapi.HTTPException(status_code=500, detail=f"Error interno del servidor: {err}")
    finally:
        cursor.close()

@app.get("/accionsformatives")
async def accionsformatives():
    cursor = connection.cursor(dictionary=True)  # Para obtener resultados como diccionarios
    try:
        cursor.execute("SELECT * FROM COURSES")
        courses = cursor.fetchall()
        return json.dumps(courses) 
    except mysql.connector.Error as err:
        raise fastapi.HTTPException(status_code=500, detail=f"Error interno del servidor: {err}")
    finally:
        cursor.close()

@app.post("/uploadfirstpage")
async def uploadfirstpage(files: List[fastapi.UploadFile], username: str = fastapi.Header(None)):
    if not username:
        raise fastapi.exceptions.HTTPException(status_code=400, detail="Username header is missing")

    save_path = os.path.join("/app/files", username, "first_page")
    os.makedirs(save_path, exist_ok=True)

    for file in files:
        file_path = os.path.join(save_path, file.filename)
        try:
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            raise fastapi.exceptions.HTTPException(status_code=500, detail=f"Failed to save file: {e}")
        finally:
            file.file.close()

    return {"state": 200, "username": username}


@app.post("/process")
async def process(request: fastapi.Request, username: str = fastapi.Header(None)):

    print("Directorio actual:", os.getcwd())

    data = await request.json()

    exp_number = data.get("exp_number")
    accio_formativa = data.get("accio_formativa")
    group_number = data.get("group_number")
    v_modality = data.get("v_modality")
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not username:
        raise fastapi.exceptions.HTTPException(status_code=400, detail="Username header is missing")

    try:
        process = await asyncio.create_subprocess_exec(
            'python', 'ml_module/responses.py', str("files/" + username + "/first_page"), username, exp_number, accio_formativa, group_number, v_modality, start_date, end_date,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        if stdout:
            print(f"Salida estándar: {stdout.decode()}")
        if stderr:
            print(f"Error estándar: {stderr.decode()}")
    except Exception as e:
        print("Error al ejecutar el comando: ", e)

    return "Processing " + str(username)


@app.get("/humancheckimages/{username}")
async def humancheckimages(username: str, image_index: int):
    print("Directorio actual HUMANCHECKIMAGES:", os.getcwd())
    
    folder_path = f"human_check/{username}"

    images_data = []

    if os.path.exists(folder_path) and os.path.isdir(folder_path):
        all_files = os.listdir(folder_path)

        for file in all_files:
            if file.lower().endswith(".png"):
                image_path = os.path.join(folder_path, file)
                with open(image_path, "rb") as image_file:
                    image_data = image_file.read()
                images_data.append((file, image_data))  # Añadir nombre de la imagen junto con sus datos

    if 0 <= image_index < len(images_data):
        image_name, image_data = images_data[image_index]
        image_array = np.frombuffer(image_data, dtype=np.uint8).tolist()  # Convertir los datos de la imagen a una lista de enteros Uint8
        response_data = {"image": image_array, "imagename": image_name}
        return response_data
    else:
        raise fastapi.HTTPException(status_code=404, detail="Item not found")
    
@app.post("/savecv")
async def savecv(request: fastapi.Request):
    data = await request.json()

    uuid = str(data.get("uuid"))
    username = str(data.get("username"))
    exp_number = str(data.get("exp_number"))
    accio_formativa = int(data.get("accio_formativa"))
    group_number = int(data.get("group_number"))
    v_modality = str(data.get("v_modality"))
    start_date = str(data.get("start_date"))
    end_date = str(data.get("end_date"))
    q1 = 0 #Age not verified
    q2 = int(data.get("0"))
    q3 = int(data.get("1"))
    q4 = int(data.get("2"))
    q5_1 = int(data.get("3"))
    q5_2 = int(data.get("4"))
    q6 = int(data.get("5"))
    q7 = int(data.get("6"))
    q8_1 = int(data.get("7"))
    q8_2 = int(data.get("8"))
    q9 = int(data.get("9"))

    cursor = connection.cursor()
    try:
        cursor.execute("INSERT INTO ANSWERS (UUID, processed_by, num_expedient, accio_formativa, grup, modalitat, data_inici, data_final, q1, q2, q3, q4, q5_1, q5_2, q6, q7, q8_1, q8_2, q9) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
               (uuid, username, exp_number, accio_formativa, group_number, v_modality, start_date, end_date, q1, q2, q3, q4, q5_1, q5_2, q6, q7, q8_1, q8_2, q9))
        connection.commit()
        return {"message": "Datos guardados correctamente en la base de datos"}
    except mysql.connector.Error as err:
        print(err)
        raise fastapi.HTTPException(status_code=500, detail=f"Error interno del servidor: {err}")
    finally:
        cursor.close()

@app.post("/updateanswer/{response_uuid}/{question_number}")
async def updateanswer(request: fastapi.Request, response_uuid: str, question_number:int):
    data = await request.json()
    print("UUID:", response_uuid)
    response1 = data.get("resposta1")
    response2 = data.get("resposta2")
    
    response1 = 0 if not response1 else int(response1)
    response2 = 0 if not response2 else int(response2)

    question_number = str(int(question_number) + 2) + "_1" if question_number == 3 else str(int(question_number) +1) + "_2"
    question_number = "q" + question_number
    print("Question Number",question_number)

    concatenated_response = str(response1) + str(response2)
    print("Concatenated Response", concatenated_response)
    try:
        cursor = connection.cursor()
        cursor.execute(f"UPDATE ANSWERS SET {question_number} = {concatenated_response} WHERE UUID = '{response_uuid}'")
        connection.commit()
        return {"message": "Datos actualizados correctamente en la base de datos"}
    except mysql.connector.Error as err:
        raise fastapi.HTTPException(status_code=500, detail=f"Error interno del servidor: {err}")


@app.delete("/deleteimage/{username}/{image_name}") # TODO: REVISAR GENERADO POR COPILOT
async def deleteimage(image_name: str, username: str):
    image_path = f"human_check/{username}/{image_name}"
    if os.path.exists(image_path):
        os.remove(image_path)
        return {"message": "Imagen eliminada correctamente"}
    else:
        raise fastapi.HTTPException(status_code=404, detail="Imagen no encontrada")

if __name__ == "__main__":
    connect_db()
    uvicorn.run(app, host="0.0.0.0", port=8081)