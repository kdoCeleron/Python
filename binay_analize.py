
def _print_byte_array(byte_array: [int], separator: str):
    length = len(byte_array)

    for ii in range(0, length):
        print(format(byte_array[ii], '02x'), end=separator)


if __name__ == "__main__":
    f = open("ECIF01_TSUSHIN", 'rb')
    data = f.read()
    size = len(data)

    buffer = []
    index = 0
    sep_num = 4  # ここに1データあたりのバイト数を設定
    while True:
        row_buffer = []
        for tmp_index in range(0, sep_num):
            tmp = data[index + tmp_index]
            row_buffer.append(tmp)

        _print_byte_array(row_buffer, " ")

        print()
        buffer.append(row_buffer)
        index += sep_num

        # カウント数が配列の長さを超えたらループ終了
        if index >= size:
            break

    print()

    # ここに必要なデータの位置を指定
    take_start = 0
    take_num = 4
    for row in buffer:
        row = row[take_start:take_start+take_num]
        _print_byte_array(row, "")
        print(f" -> {int.from_bytes(row, byteorder='little')}", end="")
        print()

