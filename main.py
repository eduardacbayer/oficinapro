# =========================
# CLASSES
# =========================

class Cliente:
    def __init__(self, codigo, nome, telefone, email):
        self.codigo = codigo
        self.nome = nome
        self.telefone = telefone
        self.email = email


class Veiculo:
    def __init__(self, placa, marca, modelo, ano, cliente):
        self.placa = placa
        self.marca = marca
        self.modelo = modelo
        self.ano = ano
        self.cliente = cliente


# =========================
# LISTAS
# =========================

clientes = []
veiculos = []


# =========================
# FUNÇÕES
# =========================

def cadastrar_cliente():
    pass


def consultar_cliente():
    pass


def cadastrar_veiculo():
    pass


def consultar_veiculo():
    pass


# =========================
# MENU PRINCIPAL
# =========================

def menu_principal():
    while True:
        print("\n===== OFICINA PRO =====")
        print("1 - Cadastrar Cliente")
        print("2 - Consultar Cliente")
        print("3 - Cadastrar Veículo")
        print("4 - Consultar Veículo")
        print("0 - Sair")

        opcao = input("\nEscolha: ")

        if opcao == "1":
            cadastrar_cliente()

        elif opcao == "2":
            consultar_cliente()

        elif opcao == "3":
            cadastrar_veiculo()

        elif opcao == "4":
            consultar_veiculo()

        elif opcao == "0":
            print("Encerrando sistema...")
            break

        else:
            print("Opção inválida!")


# =========================
# EXECUÇÃO
# =========================

menu_principal()
