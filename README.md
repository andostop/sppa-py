# ChefIA

ChefIA es una aplicación web desarrollada con Flask que recomienda comidas personalizadas mediante el uso de datos del usuario y un modelo de machine learning.

## Descripción

El sistema analiza información del usuario como peso, altura, edad, presupuesto diario, alergias, región y hábitos de consumo para generar recomendaciones de platos adecuados según el momento del día.

## Funcionalidades

- Registro e inicio de sesión de usuarios
- Edición de perfil
- Recomendación de comidas según:
  - Desayuno
  - Almuerzo
  - Cena
  - Snack
- Filtrado de platos según alergias
- Control de presupuesto diario
- Sistema de historial de consumo
- Motor de recomendación basado en machine learning

## Tecnologías utilizadas

- Python
- Flask
- Pandas
- Scikit-learn
- Joblib
- HTML / CSS (Jinja2 templates)
- Excel como base de datos local

## Estructura del proyecto

ChefIA_Proyecto/
- static/
- templates/
- app.py
- Database_ChefIA.xlsx
- modelo_chef.pkl
- scaler_chef.pkl
- features_chef.pkl
- requirements.txt
- README.md

## Ejecución

Instalar dependencias:

pip install -r requirements.txt

Ejecutar la aplicación:

python app.py

Acceder en el navegador:

http://127.0.0.1:5000