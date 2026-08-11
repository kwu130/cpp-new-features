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

## Lambda 到闭包类型

编译器会为每个 Lambda 表达式生成一个唯一、不可直接命名的闭包类，并把函数体变成 `operator()`。即使文本完全相同，两个 Lambda 表达式的闭包类型也不同。`auto` 能直接保存具体闭包类型，因此通常比 `std::function` 更轻量。

概念上，`[factor](int x) { return x * factor; }` 接近一个拥有 `factor` 数据成员和调用运算符的类。标准没有规定成员布局与名称，但允许编译器像优化普通类一样内联调用、消除未使用捕获。

无捕获 Lambda 可以转换为同签名函数指针；有捕获 Lambda 需要对象状态，不能进行这种转换。闭包的 `operator()` 默认是 `const`，所以按值捕获成员不可修改，`mutable` 会移除这一限制。

## 捕获语义与生命周期

按值捕获在创建闭包时复制当前值，之后外围变量改变不影响副本。按引用捕获通常只保存能够访问原对象的引用语义；闭包不会延长对象生命周期。异步任务、事件循环和对象成员回调是悬空引用高发区域。

在成员函数中使用成员会捕获 `this` 指针，而不是分别复制每个成员。即使写 `[=]`，C++11 中仍是复制指针；对象销毁后回调访问成员会悬空。长期回调应考虑捕获拥有对象的 `shared_ptr` 或可检测失效的 `weak_ptr`，并审查可能形成的所有权环。

## 调用与性能模型

直接以模板参数接收 Lambda 时，编译器知道闭包具体类型，通常可以完全内联。存入 `std::function` 会进行类型擦除，可能引入间接调用和堆分配；具体是否分配取决于实现的小对象优化和闭包大小。

捕获大型对象会增大闭包，每次复制回调也会复制这些成员。可移动但不可复制的资源在 C++11 中较难直接捕获，C++14 初始化捕获解决了这一问题。

## 示例解析与常见错误

主示例第一个 Lambda 按值捕获阈值，使谓词独立于后续变量修改；第二个按引用捕获计数器，让每次调用更新外围状态。算法可能复制谓词，因此不要依赖闭包副本之间共享的内部可变计数，除非共享状态是显式设计。

检查回调生命周期是否超过捕获对象；确认算法是否允许复制或并发调用回调；避免默认捕获掩盖真实依赖；高频路径测量 `std::function` 类型擦除成本。

## 权威资料

- [Lambda 表达式](https://eel.is/c++draft/expr.prim.lambda)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
