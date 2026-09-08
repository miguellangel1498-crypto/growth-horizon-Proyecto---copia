from extensions import db


ROL_SUPERADMIN = "superadmin"
ROL_EMPRESA = "empresa"
ROL_EMPLEADO = "empleado"
# Alias para compatibilidad con código antiguo que aún lo importe
ROL_ANALISTA = "empleado"


ROLES_DISPONIBLES = {
    ROL_SUPERADMIN: "Superadministrador",
    ROL_EMPRESA: "Administrador de Empresa",
    ROL_EMPLEADO: "Empleado / Vendedor",
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
    },
    {
        "permiso": "Crear / editar / eliminar empresas",
        "superadmin": True,
        "empresa": False,
        "empleado": False,
    },
    {
        "permiso": "Aprobar o suspender empresas",
        "superadmin": True,
        "empresa": False,
        "empleado": False,
    },
    {
        "permiso": "Registro de auditoría global",
        "superadmin": True,
        "empresa": False,
        "empleado": False,
    },
    {
        "permiso": "Gestionar sectores",
        "superadmin": True,
        "empresa": False,
        "empleado": False,
    },
    {
        "permiso": "Panel de su propia empresa",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
    },
    {
        "permiso": "Administrar productos (crear/editar/eliminar)",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
    },
    {
        "permiso": "Consultar inventario y precios",
        "superadmin": False,
        "empresa": True,
        "empleado": True,
    },
    {
        "permiso": "Buscar productos",
        "superadmin": False,
        "empresa": True,
        "empleado": True,
    },
    {
        "permiso": "Configuración y horarios",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
    },
    {
        "permiso": "Registrar ventas",
        "superadmin": False,
        "empresa": True,
        "empleado": True,
    },
    {
        "permiso": "Agregar inventario nuevo",
        "superadmin": False,
        "empresa": True,
        "empleado": True,
    },
    {
        "permiso": "Reportes financieros (COP)",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
    },
    {
        "permiso": "Exportar reportes (Excel)",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
    },
    {
        "permiso": "Gestionar empleados",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
    },
    {
        "permiso": "Análisis de negocio",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
    },
    {
        "permiso": "Auditoría de seguridad empresa",
        "superadmin": False,
        "empresa": True,
        "empleado": False,
    },
]


def rol_tiene_permiso(rol, clave):
    for fila in MATRIZ_PERMISOS:
        if fila["permiso"] == clave:
            return fila.get(rol, False)
    return False
