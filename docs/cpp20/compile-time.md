# `consteval`、`constinit` 与扩展 `constexpr`

`consteval` 函数必须在编译期求值；`constinit` 保证静态或线程存储期对象进行静态初始化，但不会让对象自动变成常量。C++20 继续扩大 `constexpr` 可执行操作范围。

<!-- example id="cpp20-compile-time" std="c++20" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <array>
#include <iostream>

consteval int twice(int value) {
    return value * 2;
}

constexpr int sum(std::array<int, 3> values) {
    int result = 0;
    for (const int value : values) {
        result += value;
    }
    return result;
}

constinit int runtime_counter = twice(20);

int main() {
    constexpr int offset = sum({0, 1, 1});
    ++runtime_counter;
    std::cout << runtime_counter + offset - 1 << '\n';
}
```

`constinit` 与 `constexpr` 解决不同问题：前者约束初始化时机，后者约束对象可变性与常量表达式资格。只在调用本质上必须编译期完成时使用 `consteval`。

## 三个关键字的职责

`constexpr` 表示变量是常量表达式候选或函数可参与常量求值；`consteval` 把函数声明为立即函数，每个潜在求值调用都必须产生编译期结果；`constinit` 只适用于静态或线程存储期变量，要求静态初始化但不增加 const 限定。

立即函数仍有普通函数体语法，却不能像普通运行期函数那样取得可常规调用的函数指针。它适合编译期解析字面量、生成标识和验证配置，失败应产生清晰编译诊断。

## 静态初始化顺序

全局对象若需要动态初始化，跨翻译单元依赖可能出现静态初始化顺序问题。`constinit` 强制初始化在动态初始化阶段之前完成，编译器无法证明时直接拒绝。它不解决对象销毁顺序，也不让后续并发修改自动安全。

实现通常把常量初始化结果直接放入数据段，或用零初始化完成初始状态。`runtime_counter` 因此可以在 `main` 前可靠为 40，同时仍允许运行期递增。

## C++20 `constexpr` 扩展

C++20 允许更多对象生命周期操作和标准库函数进入常量求值，包括在受限条件下动态分配，只要分配在常量求值结束前释放。许多容器能力开始逐步 `constexpr` 化，但具体设施仍需查对应标准版本。

编译器的常量求值器会跟踪对象生命周期、越界、未初始化读取和泄漏；一些运行期未定义行为因此可在强制常量上下文提前诊断。

## 成本与实践

把计算前移可减少启动工作并验证不变量，但会增加构建时间和模板/常量求值资源。对大表生成测量干净与增量构建，必要时改用生成文件或运行期缓存。

示例用 `consteval` 生成初始值、`constinit` 保证全局初始化，并用更灵活的 `constexpr` 循环求和。选择关键字时先回答：是否必须编译期调用、对象是否必须不可变、还是只需要可靠初始化时机。
