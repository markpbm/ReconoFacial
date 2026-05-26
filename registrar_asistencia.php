<?php
header("Content-Type: application/json");

$TOKEN_SECRETO = "MI_TOKEN_SECRETO_123";

$token = $_POST["token"] ?? "";
$iddocente = $_POST["iddocente"] ?? "";

if ($token !== $TOKEN_SECRETO) {
    echo json_encode([
        "ok" => false,
        "mensaje" => "Token inválido"
    ]);
    exit;
}

if ($iddocente == "") {
    echo json_encode([
        "ok" => false,
        "mensaje" => "No se recibió iddocente"
    ]);
    exit;
}

$host = "localhost";
$user = "USUARIO_HOSTING";
$password = "PASSWORD_HOSTING";
$database = "premiumc_pcoll";

$conexion = new mysqli($host, $user, $password, $database);

if ($conexion->connect_error) {
    echo json_encode([
        "ok" => false,
        "mensaje" => "Error de conexión"
    ]);
    exit;
}

$conexion->set_charset("utf8");

date_default_timezone_set("America/Lima");

$fecha = date("Y-m-d");
$hora = date("H:i:s");
$hora_actual = strtotime($hora);

$TIPO_ENTRADA = 1;
$TIPO_SALIDA = 2;

// Ajusta según tu año escolar activo
$idanio = 7;

// RANGOS HORARIOS
$hora_11 = strtotime("11:00:00");
$hora_12 = strtotime("12:00:00");
$hora_19 = strtotime("19:00:00");

// Determinar tipo de marca según la hora
if ($hora_actual < $hora_11) {
    $idtipo = $TIPO_ENTRADA;
    $bloque_inicio = "00:00:00";
    $bloque_fin = "10:59:59";
    $accion = "entrada_manana";
    $mensaje_ok = "Entrada de mañana registrada";
    $mensaje_duplicado = "Ya registró entrada de mañana";
} 
elseif ($hora_actual >= $hora_11 && $hora_actual < $hora_12) {
    $idtipo = $TIPO_SALIDA;
    $bloque_inicio = "11:00:00";
    $bloque_fin = "11:59:59";
    $accion = "salida_manana";
    $mensaje_ok = "Salida de mañana registrada";
    $mensaje_duplicado = "Ya registró salida de mañana";
} 
elseif ($hora_actual >= $hora_12 && $hora_actual < $hora_19) {
    $idtipo = $TIPO_ENTRADA;
    $bloque_inicio = "12:00:00";
    $bloque_fin = "18:59:59";
    $accion = "entrada_tarde";
    $mensaje_ok = "Entrada de tarde registrada";
    $mensaje_duplicado = "Ya registró entrada de tarde";
} 
else {
    $idtipo = $TIPO_SALIDA;
    $bloque_inicio = "19:00:00";
    $bloque_fin = "23:59:59";
    $accion = "salida_tarde";
    $mensaje_ok = "Salida de tarde registrada";
    $mensaje_duplicado = "Ya registró salida de tarde";
}

// Verificar si ya existe marca en ese bloque
$sql_buscar = "
    SELECT idasistenciaPersonal
    FROM asistenciapersonal
    WHERE iddocente = ?
      AND fecha = ?
      AND idtipo = ?
      AND hora BETWEEN ? AND ?
    LIMIT 1
";

$stmt = $conexion->prepare($sql_buscar);
$stmt->bind_param("isiss", $iddocente, $fecha, $idtipo, $bloque_inicio, $bloque_fin);
$stmt->execute();

$resultado = $stmt->get_result();

if ($resultado->num_rows > 0) {
    echo json_encode([
        "ok" => true,
        "accion" => "duplicado",
        "mensaje" => $mensaje_duplicado
    ]);
    exit;
}

// Insertar nueva marca
$sql_insertar = "
    INSERT INTO asistenciapersonal
    (iddocente, idtipo, idanio, fecha, hora, est)
    VALUES (?, ?, ?, ?, ?, 1)
";

$stmt_insert = $conexion->prepare($sql_insertar);
$stmt_insert->bind_param("iiiss", $iddocente, $idtipo, $idanio, $fecha, $hora);

if ($stmt_insert->execute()) {
    echo json_encode([
        "ok" => true,
        "accion" => $accion,
        "mensaje" => $mensaje_ok
    ]);
    exit;
} else {
    echo json_encode([
        "ok" => false,
        "accion" => "error_insert",
        "mensaje" => "No se pudo registrar asistencia"
    ]);
    exit;
}
?>