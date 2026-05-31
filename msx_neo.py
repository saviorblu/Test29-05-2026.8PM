stopimport os, json, subprocess, time, zipfile, shutil
from datetime import datetime

# ================================
# MSX NEO - Launcher para NeoForge
# Uso: python3 msx_neo.py
# ================================

SERVIDOR   = "servidor_minecraft"
CONFIG     = "configuracion.json"
RESPALDOS  = "respaldos"
ADDONS     = "addons"

def leer_config():
    if os.path.exists(CONFIG):
        with open(CONFIG) as f:
            return json.load(f)
    return {}

def iniciar_tailscale():
    print("[+] Iniciando Tailscale...")
    os.system("sudo bash ./tailscale-cs/iniciar.sh > tailscale_log.txt 2>&1 &")
    time.sleep(4)
    os.system("sudo tailscale up --accept-routes 2>/dev/null")
    ip = subprocess.getoutput("sudo tailscale ip 2>/dev/null").split("\n")[0].strip()
    if ip:
        print("[+] Tailscale iniciado!")
        print("[+] Autentificado e iniciado!")
        print(f"[+] La IP del servidor es: {ip}")
    else:
        print("[!] No se pudo obtener IP. Revisa tailscale_log.txt")

def sincronizar_mods():
    mods_origen  = os.path.join(ADDONS, "mods")
    mods_destino = os.path.join(SERVIDOR, "mods")

    if not os.path.exists(mods_origen):
        os.makedirs(mods_origen, exist_ok=True)
        print(f"[+] Carpeta de mods creada en: {mods_origen}/")
        return

    os.makedirs(mods_destino, exist_ok=True)

    jars = [f for f in os.listdir(mods_origen) if f.endswith(".jar")]
    if not jars:
        print("[+] Sin mods nuevos en addons/mods/")
        return

    copiados = 0
    for jar in jars:
        src  = os.path.join(mods_origen, jar)
        dest = os.path.join(mods_destino, jar)
        if not os.path.exists(dest):
            shutil.copy2(src, dest)
            print(f"[+] Mod instalado: {jar}")
            copiados += 1

    if copiados == 0:
        print(f"[+] Todos los mods ya estaban instalados ({len(jars)} mods)")
    else:
        print(f"[+] {copiados} mod(s) instalado(s) correctamente")

def comprimir_mundo():
    world_path = os.path.join(SERVIDOR, "world")
    if not os.path.exists(world_path):
        print("[-] No se encontró la carpeta world/")
        return None

    os.makedirs(RESPALDOS, exist_ok=True)
    zip_path = os.path.join(RESPALDOS, "world_respaldo.zip")

    print("[+] Comprimiendo mundo...")
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(world_path):
            for file in files:
                filepath = os.path.join(root, file)
                arcname  = os.path.relpath(filepath, SERVIDOR)
                zipf.write(filepath, arcname)

    size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"[+] Mundo comprimido: {size_mb:.1f} MB")
    return size_mb

def guardar_repositorio(modo="luna"):
    print("\n[+] Guardando mundo en el repositorio...")

    if subprocess.run("git status", shell=True, capture_output=True).returncode != 0:
        print("[-] No se detectó repositorio git. Saltando guardado.")
        return

    size_mb = comprimir_mundo()
    if size_mb is None:
        return

    if size_mb > 100:
        print(f"[!] ATENCIÓN: Tu respaldo pesa {size_mb:.1f} Mb, puede tener problemas en GitHub.")
        print("    Considera usar: https://www.curseforge.com/minecraft/mc-mods/cloudbackup")

    fecha = datetime.now().strftime("%Y-%m-%d")

    if modo == "luna":
        print("[+] Modo 🌙 Luna: reiniciando historial del repositorio...")
        os.system("git add .")
        os.system("git diff --cached --name-only | xargs -I {} bash -c '[[ $(stat -c%s \"{}\") -gt 100000000 ]] && git restore --staged \"{}\"' 2>/dev/null")
        os.system("git checkout --orphan temp_branch 2>/dev/null")
        os.system("git add -A")
        os.system(f'git commit -m "[🌙] Historial reiniciado {fecha}"')
        os.system("git branch -D main 2>/dev/null")
        os.system("git branch -m main")
        resultado = os.system("git push -f origin main")
    else:
        os.system("git reset --mixed origin/main 2>/dev/null")
        os.system("git add respaldos/*")
        resultado = os.system(f'git commit -m "Mundo guardado {fecha}" && git push')

    if resultado == 0:
        print("[+] ¡Mundo guardado en el repositorio!")
    else:
        print("[!] Error al subir. Verifica los permisos del repositorio.")

def iniciar_neoforge(cfg):
    run_sh = os.path.join(SERVIDOR, "run.sh")
    if not os.path.exists(run_sh):
        print(f"[-] No se encontró {run_sh}")
        print(f"    Instala NeoForge primero:")
        print(f"    cd {SERVIDOR} && java -jar neoforge-*.jar --installServer")
        input("\n[SERVIDOR APAGADO] Enter para continuar......")
        return

    sincronizar_mods()

    print("[+] Iniciando servidor NeoForge...\n")
    os.chdir(SERVIDOR)
    os.system("bash run.sh nogui")
    os.chdir("..")

    if cfg.get("backup_auto", True):
        modo = cfg.get("backup_mode", "luna")
        guardar_repositorio(modo)

    input("\n[SERVIDOR APAGADO] Enter para continuar......")

def main():
    cfg      = leer_config()
    servicio = cfg.get("servicio_a_usar", "tailscale")

    if servicio == "tailscale":
        iniciar_tailscale()
    elif servicio == "local":
        print("[+] Modo local, sin túnel.")

    iniciar_neoforge(cfg)

main()
