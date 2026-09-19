# Use PyMySQL (pure Python, installs on Windows without a C compiler)
# as the MySQL driver Django expects.
try:
    import pymysql

    pymysql.install_as_MySQLdb()
except ImportError:  # MySQL not used
    pass