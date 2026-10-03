SISTEMA DE VENTAS DE BODEGÓN
============================

Este programa es 100% Python + Tkinter + SQLite, así que corre igual en
Windows, Mac o Linux. No tiene nada específico de un sistema operativo.

REQUISITOS
----------
- Python 3.9 o superior. En Windows descárgalo de https://www.python.org/downloads/
  IMPORTANTE: al instalarlo, marca la casilla "Add python.exe to PATH".
  Tkinter ya viene incluido en el instalador de Windows, no hay que
  instalar nada aparte.
- Conexión a internet (opcional, solo para traer la tasa BCV automática)
- (Solo si algún día lo corres en Linux: a veces hay que instalar Tkinter
  aparte con "sudo apt install python3-tk")

INSTALACIÓN Y EJECUCIÓN EN WINDOWS (la forma fácil)
-----------------------------------------------------
1. Descomprime esta carpeta donde quieras (por ejemplo en el Escritorio).
2. Haz doble clic en "instalar.bat" (solo la primera vez, instala la
   única dependencia externa: la librería requests).
3. Haz doble clic en "iniciar.bat" para abrir el programa.
   (Si Windows muestra una advertencia de "Windows protegió su PC",
   dale clic en "Más información" -> "Ejecutar de todas formas";
   es normal para archivos .bat que no tienen firma digital).

INSTALACIÓN Y EJECUCIÓN MANUAL (Windows, Mac o Linux, por terminal)
----------------------------------------------------------------------
1. Abre una terminal (en Windows: cmd o PowerShell) dentro de esta carpeta.
2. Instala la dependencia:
       pip install -r requirements.txt
   (en Windows a veces el comando es "py -m pip install -r requirements.txt")
3. Ejecuta el programa:
       python main.py
   (en Windows a veces el comando es "py main.py")

USUARIOS DE PRUEBA (se crean automáticamente la primera vez)
--------------------------------------------------------------
  Administrador:  usuario = admin    contraseña = admin123
  Cajero:         usuario = cajero   contraseña = cajero123

Puedes crear más usuarios desde el panel de Administrador > pestaña Usuarios,
y cambiar estas contraseñas por defecto cuando quieras.

CÓMO FUNCIONA
-------------
- Al iniciar sesión como ADMIN entras al panel de administración:
    * Productos/Inventario: agregar, editar, ajustar stock y eliminar productos.
      Se resaltan en rojo los que están por agotarse.
    * Reportes de ventas: totales de hoy/semana/mes, productos más vendidos,
      generar un "registro diario" (bitácora .txt de ventas y movimientos)
      y hacer un respaldo (backup) de la base de datos.
    * Tasa BCV: tres pestañas -> Dólar BCV (automática), Euro BCV (automática,
      solo informativa) y Dólar Manual (la fijas tú). En Dólar BCV y Dólar
      Manual hay un botón "Usar esta tasa para cobrar" para elegir con cuál
      se calculan los totales en bolívares al vender.
    * Usuarios: crear cajeros/administradores, cambiar contraseñas o
      desactivar usuarios.
  Arriba de todo hay una barra fija (la "leyenda") con las 3 tasas visibles
  en todo momento, sin tener que entrar a ninguna pestaña.

- Al iniciar sesión como CAJERO entras al punto de venta:
    * Buscas productos, los agregas al carrito con la cantidad deseada.
    * Puedes buscar un cliente existente o registrar uno nuevo (nombre +
      teléfono + cédula) o marcarlo como "frecuente" (solo nombre).
    * Eliges la forma de pago y presionas COBRAR. Se descuenta el stock,
      se guarda la venta y se genera un ticket (se muestra en pantalla y
      se guarda como .txt en la carpeta "tickets/").
  La misma barra de tasas está visible arriba para consultar el dólar de
  un vistazo mientras cobras.

SEGURIDAD DE INICIO DE SESIÓN
------------------------------
Tras 3 intentos fallidos de contraseña, el usuario queda bloqueado durante
3 minutos antes de poder volver a intentarlo.

ARCHIVOS QUE GENERA EL PROGRAMA
---------------------------------
  bodegon.db        -> la base de datos (no la borres si quieres conservar
                        tus productos, clientes y ventas)
  tickets/           -> un .txt por cada venta realizada
  registros/         -> un .txt por día con el resumen de ventas y movimientos
  backups/           -> copias de bodegon.db con fecha y hora, cuando pidas
                        "Respaldar base de datos" desde el panel admin
