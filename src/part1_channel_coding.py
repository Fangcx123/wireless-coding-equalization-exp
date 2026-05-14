"""
Part 1：信道编码实验

学生需要完成 Hamming(7,4) 编码、伴随式计算和单比特纠错译码。
选做内容包括卷积码编码和 Viterbi 硬判决译码。
"""

import numpy as np
# pylint: disable=import-error
from utils import (
    binary_symmetric_channel,
    calculate_ber,
    generate_bits,
    plot_ber_curve,
)

HAMMING_G = np.array([
    [1, 0, 0, 0, 1, 1, 0],
    [0, 1, 0, 0, 1, 0, 1],
    [0, 0, 1, 0, 0, 1, 1],
    [0, 0, 0, 1, 1, 1, 1],
], dtype=int)

HAMMING_H = np.array([
    [1, 1, 0, 1, 1, 0, 0],
    [1, 0, 1, 1, 0, 1, 0],
    [0, 1, 1, 1, 0, 0, 1],
], dtype=int)


def hamming74_encode(bits):
    """
    Hamming(7,4) 系统码编码。

    参数:
        bits: 一维 0/1 数组，长度必须是 4 的倍数。

    返回:
        encoded: 一维 0/1 编码比特数组，长度为输入的 7/4 倍。

    要求:
        使用课件中的生成矩阵 G，按 GF(2) 进行矩阵乘法。
    """
    bits = np.asarray(bits, dtype=int)
    if bits.ndim != 1:
        raise ValueError('bits 必须是一维数组')
    if len(bits) % 4 != 0:
        raise ValueError('Hamming(7,4) 要求输入长度为 4 的倍数')
    if not np.all((bits == 0) | (bits == 1)):
        raise ValueError('bits 只能包含 0 或 1')

    blocks = bits.reshape(-1, 4)
    codewords = (blocks @ HAMMING_G) % 2
    return codewords.flatten()


def hamming74_syndrome(codewords):
    """
    计算 Hamming(7,4) 码字的伴随式。

    参数:
        codewords: 一维或二维 0/1 数组。若为一维，长度必须是 7 的倍数。

    返回:
        syndromes: 形状为 (N, 3) 的伴随式数组。
    """
    codewords = np.asarray(codewords, dtype=int)
    if codewords.ndim == 1:
        if len(codewords) % 7 != 0:
            raise ValueError('码字长度必须是 7 的倍数')
        codewords = codewords.reshape(-1, 7)
    if codewords.shape[1] != 7:
        raise ValueError('每个 Hamming(7,4) 码字长度必须为 7')

    return (codewords @ HAMMING_H.T) % 2


def hamming74_decode(received):
    """
    Hamming(7,4) 单比特纠错译码。

    参数:
        received: 一维 0/1 接收序列，长度必须是 7 的倍数。

    返回:
        decoded_bits: 纠错后提取出的信息比特序列。

    提示:
        1. 计算每个码字的伴随式。
        2. 若伴随式非零，将其与 H 的各列比较，定位错误比特。
        3. 翻转对应错误位。
        4. 系统码的信息位为前 4 位。
    """
    received = np.asarray(received, dtype=int)
    if received.ndim != 1 or len(received) % 7 != 0:
        raise ValueError('received 必须是一维数组，长度为 7 的倍数')

    codewords = received.reshape(-1, 7).copy()
    syndromes = hamming74_syndrome(codewords)
    for i, s in enumerate(syndromes):
        if s.any():
            error_pos = np.argwhere((HAMMING_H.T == s).all(axis=1)).item()
            codewords[i, error_pos] ^= 1
    return codewords[:, :4].flatten()


def convolutional_encode(bits):
    """
    选做：实现 (2,1,3) 卷积码编码，生成多项式为 g1=111, g2=101。

    默认在末尾添加 2 个 0 作为尾比特，使状态回到全零。
    """
    bits = np.asarray(bits, dtype=int)
    if not np.all((bits == 0) | (bits == 1)):
        raise ValueError('bits 只能包含 0 或 1')

    bits_with_tail = np.append(bits, [0, 0])
    delayed_1, delayed_2 = 0, 0
    encoded = []
    for bit in bits_with_tail:
        # g1=111: bit ⊕ d1 ⊕ d2
        # g2=101: bit ⊕ d2
        encoded.extend([bit ^ delayed_1 ^ delayed_2, bit ^ delayed_2])
        delayed_2 = delayed_1
        delayed_1 = bit
    return np.array(encoded, dtype=int)


def viterbi_decode_hard(received_bits):
    """
    选做：实现 (2,1,3) 卷积码硬判决 Viterbi 译码。
    """
    received_bits = np.asarray(received_bits, dtype=int)
    if len(received_bits) % 2 != 0:
        raise ValueError('卷积码接收序列长度必须是 2 的倍数')

    # Trellis: next_state[curr][input] = (next, (out1, out2))
    # States: 0=00, 1=01, 2=10, 3=11
    trellis = {
        0: {0: (0, (0, 0)), 1: (2, (1, 1))},
        1: {0: (0, (1, 1)), 1: (2, (0, 0))},
        2: {0: (1, (1, 0)), 1: (3, (0, 1))},
        3: {0: (1, (0, 1)), 1: (3, (1, 0))},
    }

    num_steps = len(received_bits) // 2
    num_states = 4

    path_metrics = np.full(num_states, np.inf)
    path_metrics[0] = 0.0
    survivors = [[None] * num_states for _ in range(num_steps)]

    for step in range(num_steps):
        received_pair = received_bits[2 * step : 2 * step + 2]
        new_metrics = np.full(num_states, np.inf)
        for curr_state in range(num_states):
            if np.isinf(path_metrics[curr_state]):
                continue
            for input_bit in (0, 1):
                next_state, expected = trellis[curr_state][input_bit]
                hamming = np.sum(received_pair != np.array(expected))
                candidate = path_metrics[curr_state] + hamming
                if candidate < new_metrics[next_state]:
                    new_metrics[next_state] = candidate
                    survivors[step][next_state] = (curr_state, input_bit)
        path_metrics = new_metrics

    best_state = int(np.argmin(path_metrics))
    decoded = []
    for step in range(num_steps - 1, -1, -1):
        prev_state, input_bit = survivors[step][best_state]
        decoded.append(input_bit)
        best_state = prev_state
    decoded.reverse()
    return np.array(decoded[:-2], dtype=int)


def run_coding_demo():
    """运行 Part 1 演示并生成 BER 曲线。"""
    print('=' * 60)
    print('Part 1：信道编码实验')
    print('=' * 60)

    error_probabilities = np.array([0.001, 0.003, 0.01, 0.03, 0.06, 0.1])
    uncoded_ber = []
    coded_ber = []

    try:
        bits = generate_bits(4000, seed=2026)
        bits = bits[: len(bits) // 4 * 4]
        encoded = hamming74_encode(bits)

        for index, probability in enumerate(error_probabilities):
            uncoded_rx = binary_symmetric_channel(bits, probability, seed=100 + index)
            encoded_rx = binary_symmetric_channel(encoded, probability, seed=200 + index)
            decoded = hamming74_decode(encoded_rx)
            uncoded_ber.append(calculate_ber(bits, uncoded_rx))
            coded_ber.append(calculate_ber(bits, decoded))

        plot_ber_curve(
            error_probabilities,
            {'未编码': uncoded_ber, 'Hamming(7,4)': coded_ber},
            'Hamming(7,4) 编码前后 BER 对比',
            'coding_ber_curve.png',
        )
        print('✅ 已生成 results/coding_ber_curve.png')
    except NotImplementedError as error:
        print(f'⏸️ 尚未完成核心函数：{error}')
    except Exception as error:
        print(f'❌ Part 1 运行失败：{error}')


if __name__ == '__main__':
    run_coding_demo()
