# これはサンプルの Python スクリプトです。

# Shift+F10 を押して実行するか、ご自身のコードに置き換えてください。
# Shift を2回押す を押すと、クラス/ファイル/ツールウィンドウ/アクション/設定を検索します。

from typing import Tuple
import random


def print_hi(name) -> Tuple[int, int]:
    # スクリプトをデバッグするには以下のコード行でブレークポイントを使用してください。
    print(f'Hi, {name}')  # Ctrl+F8を押すとブレークポイントを切り替えます。
    return (123 - 100) / 100, 10


def omikuji():
    array = range(0, 100)
    for ii in range(10):
        # num = random.randint(0, 100)
        print(random.choice(array))


def lamda_test_func():
    val1 = 10
    val2 = 20
    lamda_test = lambda param1, param2: param1 * param2
    ret = lamda_test(val1, val2)
    print(ret)


# ガター内の緑色のボタンを押すとスクリプトを実行します。
if __name__ == '__main__':
    input_val = input('input any text: ')
    print(f'{input_val} input!')

    # lamda_test_func()

    tmp = "abc".replace("\\", "/")
    print(tmp)

    # omikuji()
    # ret1, ret2 = print_hi('PyCharm')
    # print(f'func ret is {ret1}, {ret2}')
    #
    # array = [1, 2, 3, 10]
    # for ii in array:
    #     print(f'print {ii}')

# PyCharm のヘルプは https://www.jetbrains.com/help/pycharm/ を参照してください
