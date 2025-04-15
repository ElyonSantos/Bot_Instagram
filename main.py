import os
import time
import json
import random
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pyautogui

# Configuração inicial
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CREDENTIALS_FILE = os.path.join(BASE_DIR, "credentials.json")
POSITION_FILE = os.path.join(BASE_DIR, "position.json")

def load_json(file_path):
    """Carrega dados de um arquivo JSON."""
    if os.path.exists(file_path):
        with open(file_path, "r") as file:
            return json.load(file)
    return None

def save_json(data, file_path):
    """Salva dados em um arquivo JSON."""
    with open(file_path, "w") as file:
        # noinspection PyTypeChecker
        json.dump(data, file)

def get_position(prompt_message):
    """Obtém a posição do mouse usando pyautogui."""
    print(prompt_message)
    time.sleep(10)  # Espera 10 segundos para o usuário posicionar o mouse
    position = pyautogui.position()
    print(f"Posição capturada: {position}")
    return {"x": position.x, "y": position.y}

def configure_credentials():
    """Configura ou carrega credenciais do usuário."""
    credentials = load_json(CREDENTIALS_FILE)
    if credentials:
        overwrite = input("Credenciais encontradas. Deseja sobrescrever? (s/n): ").lower()
        if overwrite == "s":
            username = input("Digite seu nome de usuário do Instagram: ")
            password = input("Digite sua senha do Instagram: ")
            credentials = {"username": username, "password": password}
            save_json(credentials, CREDENTIALS_FILE)
    else:
        username = input("Digite seu nome de usuário do Instagram: ")
        password = input("Digite sua senha do Instagram: ")
        credentials = {"username": username, "password": password}
        save_json(credentials, CREDENTIALS_FILE)
    return credentials

def configure_position():
    """Configura ou carrega a posição de comentários."""
    position = load_json(POSITION_FILE)
    if position:
        new_position = input("Posição de comentário encontrada. Deseja configurar uma nova? (s/n): ").lower()
        if new_position == "s":
            position = get_position("Posicione o mouse onde deseja que os comentários sejam feitos. (10 segundos)")
            save_json(position, POSITION_FILE)
    else:
        position = get_position("Posicione o mouse onde deseja que os comentários sejam feitos. (10 segundos)")
        save_json(position, POSITION_FILE)
    return position

def login_instagram(driver, credentials):
    """Realiza o login no Instagram."""
    driver.get("https://www.instagram.com/accounts/login/")
    time.sleep(5)  # Aguarda a página carregar

    # Loop para localizar os campos de login
    for _ in range(5):  # Tenta até 5 vezes
        try:
            # Insere o nome de usuário
            username_field = driver.find_element(By.NAME, "username")
            username_field.send_keys(credentials["username"])

            # Insere a senha
            password_field = driver.find_element(By.NAME, "password")
            password_field.send_keys(credentials["password"])
            password_field.send_keys(Keys.RETURN)

            time.sleep(10)  # Aguarda o login ser processado
            break  # Sai do loop se o login for bem-sucedido
        except Exception as e:
            print(f"Tentando novamente... Erro: {e}")
            time.sleep(2)
    else:
        raise Exception("Não foi possível encontrar os campos de login após várias tentativas.")

def fetch_profiles(driver, num_profiles):
    """Busca perfis no Instagram na página de exploração."""
    driver.get("https://www.instagram.com/explore/people/")
    time.sleep(5)  # Aguarda a página carregar

    profiles = set()
    attempts = 0
    max_attempts = 10

    while len(profiles) < num_profiles and attempts < max_attempts:
        attempts += 1
        print(f"Tentativa {attempts} de seguir perfis.")

        try:
            # Espera até que os botões estejam presentes na página
            WebDriverWait(driver, 10).until(
                EC.presence_of_all_elements_located((By.TAG_NAME, "button"))
            )

            # Coleta todos os botões
            buttons = driver.find_elements(By.TAG_NAME, "button")
            follow_buttons = [btn for btn in buttons if 'Seguir' in btn.text]

            if not follow_buttons:
                print("Nenhum botão 'Seguir' visível. Recarregando a página.")
                driver.refresh()
                time.sleep(5)
                continue

            for button in follow_buttons:
                if len(profiles) >= num_profiles:
                    break

                try:
                    button.click()
                    time.sleep(5)  # Aguarda o clique ser processado

                    # Verifica se o botão mudou para "Seguindo" ou "Solicitado"
                    new_text = button.text
                    if new_text in ["Seguindo", "Solicitado"]:
                        profile_url = button.find_element(By.XPATH, "./ancestor::div//a").get_attribute("href")
                        profiles.add(profile_url)
                    else:
                        raise Exception("Botão não mudou para 'Seguindo' ou 'Solicitado'.")

                except Exception as e:
                    print(f"Erro ao clicar no botão 'Seguir': {e}")
                    raise Exception("Erro fatal ao seguir perfil.")  # Encerra o programa em caso de erro crítico

            time.sleep(3)

        except Exception as e:
            print(f"Erro ao buscar perfis: {e}")
            raise Exception("Erro fatal ao buscar perfis.")  # Encerra o programa em caso de erro crítico

    if len(profiles) < num_profiles:
        raise Exception("Número insuficiente de perfis seguidos.")

    print("Perfis indexados com sucesso.")  # Mensagem final estilosa :)
    return list(profiles)

def validate_input(total_comments, mentions_per_comment, num_profiles):
    """Valida entradas do usuário."""
    if mentions_per_comment > num_profiles:
        raise ValueError("O número de menções por comentário não pode ser maior que o número de perfis.")
    if total_comments * mentions_per_comment > num_profiles:
        raise ValueError("Não há perfis suficientes para atender às configurações.")

def post_comments(driver, profiles, total_comments, mentions_per_comment, position):
    """Faz comentários no post."""
    random.shuffle(profiles)  # Embaralha perfis para evitar repetição
    used_profiles = set()

    for _ in range(total_comments):
        comment = ""
        for _ in range(mentions_per_comment):
            profile = profiles.pop(0)
            used_profiles.add(profile)
            comment += f"@{profile.split('/')[-2]} "

        # Move o mouse para a posição de comentário
        pyautogui.moveTo(position["x"], position["y"])
        pyautogui.click()
        time.sleep(2)

        # Digita o comentário
        pyautogui.write(comment)
        pyautogui.press("enter")
        time.sleep(5)  # Aguarda o comentário ser publicado

def main():
    driver = None  # Inicializa o driver como None
    try:
        # Entradas do usuário
        num_profiles = int(input("Quantos perfis deseja indexar? "))
        mentions_per_comment = int(input("Quantas marcações deseja por comentário? "))
        total_comments = int(input("Quantos comentários deseja fazer no total? "))

        # Valida entradas
        validate_input(total_comments, mentions_per_comment, num_profiles)

        # Configurações iniciais
        position = configure_position()

        # Solicita credenciais antes de abrir o navegador
        credentials = configure_credentials()

        # Configuração do Selenium
        options = Options()
        options.add_argument("--start-maximized")
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

        # Login no Instagram
        login_instagram(driver, credentials)

        # Busca perfis
        profiles = fetch_profiles(driver, num_profiles)

        # Faz comentários
        post_comments(driver, profiles, total_comments, mentions_per_comment, position)

    except Exception as e:
        print(f"Erro fatal: {e}")
        if driver:  # Verifica se o driver foi inicializado
            driver.quit()
        exit(1)

if __name__ == "__main__":
    main()