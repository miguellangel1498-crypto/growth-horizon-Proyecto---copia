from extensions import db


ROL_SUPERADMIN = "superadmin"
ROL_EMPRESA = "empresa"
ROL_EMPLEADO = "empleado"
ROL_ANALISTA = "analista"


ROLES_DISPONIBLES = {
    ROL_SUPERADMIN: "Superadministrador",
    ROL_EMPRESA: "Administrador de Empresa",
    ROL_EMPLEADO: "Empleado",
    ROL_ANALISTA: "Analista",
}


ESTADO_EMPRESA_PENDIENTE = "pendiente"
ESTADO_EMPRESA_ACTIVO = "activo"
ESTADO_EMPRESA_RECHAZADO = "rechazado"
ESTADO_EMPRESA_INACTIVO = "inactivo"

ESTADOS_EMPRESA = [
    ESTADO_EMPRESA_PENDIENTE,
    ESTADO_EMPRESA_ACTIVO,
    ESTADO_EMPRESA_RECHAZADO,
    ESTADO_EMPRESA_INACTIVO,
]


MATRIZ_PERMISOS = [
    {
        "permiso": "Panel global / ecosistema",
        "superadmin": True,
        "empresa": False,
        "empleado": False,
        "analista": True,
    },
    {
        "permiso": "Crear / editar / eliminar empresas",
        "superadmin": True,
        "empresa": False,
        "empleado": False,
        "analista": False,
    },
    {
        "permiso": "Aprobar o suspender empresas",
        "superadmin": True,
        "empresa": False,
        "empleado": False,
        "analista": False,
    },
    {
        "permiso": "Registro de auditoría global",
        "superadmin": True,
        "empresa": False,
        "empleado": False,
        "analista": False,
    },
    {
        "permiso": "Gestionar sectores",
        "superadmin": True,
        "empresa": False,
        "empleado": False,
        "analista": False,
    },
    {
        "permiso": "Panel de su propia empresa",
        "superadmin": False,
        "empresa": True,
        "empleado": True,
        "analista": False,
    },
    {
        "permiso": "Administrar productos (crear/editar)",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
        "analista": False,
    },
    {
        "permiso": "Consultar inventario (solo lectura)",
        "superadmin": False,
        "empresa": True,
        "empleado": True,
        "analista": False,
    },
    {
        "permiso": "Configuración y horarios",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
        "analista": False,
    },
    {
        "permiso": "Registrar ventas",
        "superadmin": False,
        "empresa": True,
        "empleado": True,
        "analista": False,
    },
    {
        "permiso": "Reportes financieros (COP)",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
        "analista": False,
    },
    {
        "permiso": "Exportar reportes (Excel)",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
        "analista": False,
    },
    {
        "permiso": "Gestionar empleados",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
        "analista": False,
    },
    {
        "permiso": "Análisis de negocio",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
        "analista": False,
    },
]


def rol_tiene_permiso(rol, clave):
    for fila in MATRIZ_PERMISOS:
        if fila["permiso"] == clave:
            return fila.get(rol, False)
    return False
