# Lambda 表达式

Lambda 可以在使用位置定义匿名函数对象，非常适合算法、自定义回调和局部策略。

<!-- example id="cpp11-lambdas" std="c++11" file="main.cpp" kind="single" compilers="all" output="12" -->
```cpp
#include <algorithm>
#include <iostream>
#include <numeric>
#include <vector>

int main() {
    std::vector<int> values{1, 2, 3, 4};
    const int threshold = 2;
    values.erase(std::remove_if(values.begin(), values.end(),
                                [threshold](int value) { return value < threshold; }),
                 values.end());

    int calls = 0;
    const int sum = std::accumulate(values.begin(), values.end(), 0,
                                    [&calls](int total, int value) {
                                        ++calls;
                                        return total + value;
                                    });
    std::cout << (sum + calls) << '\n';
}
```

优先显式列出捕获项，避免 `[&]` 或 `[=]` 在长生命周期回调中意外捕获对象。按值捕获默认不可修改；需要维护内部状态时可使用 `mutable`，但应留意它修改的是闭包内部副本。

