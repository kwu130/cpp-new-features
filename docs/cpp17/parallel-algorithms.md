# 带执行策略的算法

部分标准算法新增执行策略重载。`seq` 要求顺序执行，`par` 允许多线程，`par_unseq` 还允许线程内交错或向量化执行。

<!-- example id="cpp17-execution-policies" std="c++17" file="main.cpp" kind="single" compilers="gcc" output="1 4 9 16" -->
```cpp
#include <algorithm>
#include <execution>
#include <iostream>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 3, 4};
    std::transform(std::execution::seq, values.begin(), values.end(), values.begin(),
                   [](int value) { return value * value; });
    for (const int value : values) {
        std::cout << value << (value == values.back() ? '\n' : ' ');
    }
}
```

示例使用 `seq` 以保持验证环境确定性；替换为并行策略前，回调必须避免数据竞争、锁顺序问题和对执行顺序的依赖。并行策略并不保证一定创建线程，实际收益需通过基准测试确认。

该示例由 CI 的 GCC/libstdc++ 任务验证。部分 libc++ 发行版本尚未提供标准执行策略，因此 Apple Clang 验证任务会明确跳过本例。
