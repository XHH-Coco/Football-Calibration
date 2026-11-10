"""M1 / T1.7 —— 默认随机种子（复现包的公共默认值）。

**这不是「全局设一次就万事大吉」的开关**：簇 bootstrap、HGB、任何带随机性的
步骤都必须在**各自的调用点显式传** ``random_state=DEFAULT_SEED``。
本文件只提供一个全组统一的数字，避免五个人各写一个 42。

主表构建（S1–S4）与覆盖率矩阵（S5）是**确定性**的，不需要种子；
``run_all.sh`` 调用本脚本只是为了把种子打印进复现日志，方便倒查。

运行：``python appendix/seed.py``
"""

from __future__ import annotations

DEFAULT_SEED = 20261110


def set_global_seeds(seed: int = DEFAULT_SEED) -> int:
    """给标准库 ``random`` 与 numpy 的**旧式全局 RNG**兜底设种。

    注意：``numpy.random.default_rng()`` 不读全局种子，必须显式传种子；
    ``sklearn`` 的 HGB / bootstrap 同理。此函数不能替代调用点的显式参数。
    """
    import random

    import numpy as np

    random.seed(seed)
    np.random.seed(seed)
    return seed


if __name__ == "__main__":
    set_global_seeds()
    print(f"DEFAULT_SEED = {DEFAULT_SEED}")
    print("NOTE: bootstrap / HGB must still pass random_state explicitly "
          "at each call site.")
