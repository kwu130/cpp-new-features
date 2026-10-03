# 局部语言改进：显式副本、整数后缀与调用语法

阅读前建议先了解：[类型推导](../cpp11/type-deduction.md)、[Lambda](../cpp11/lambdas.md)。本篇介绍的新增能力属于 C++23。

## 这些改进解决什么问题

很多日常代码不需要新框架，只需要更准确地表达意图：我要一个副本、我要容器长度类型、我要二维下标，或者这个函数对象根本不使用对象状态。C++23 给这些场景增加了局部语法。各小节可以独立阅读；它们不会自动改善算法复杂度。

## auto(x)：在表达式中要求一个值

以前常写 `auto copy = original;`，再把 copy 传给其他函数。`auto(original)` 可以在表达式里完成按 auto 规则推导的值初始化。它不是动态类型，也不是 `decltype(auto)` 的保留引用规则。

```cpp example id="cpp23-auto-copy" std="c++23" file="main.cpp" kind="single" compilers="all" output="source=1, copy=9"
#include <cassert>
#include <iostream>
#include <vector>
int main() {
    std::vector<int> source{1, 2};
    auto copy = auto(source);
    copy[0] = 9;
    assert(source[0] == 1);
    std::cout << "source=" << source[0] << ", copy=" << copy[0] << '\n';
}
```

这里建立了独立 vector，修改 copy 不影响 source。用于要求按值传入的表达式很直观，但并非任何类型都会深复制：指针的副本仍指向同一对象，代理类型的副本也可能继续引用原数据。数组按 auto 的普通推导规则退化为指针；不可复制类型的左值不能用它强行复制。

## z 与 uz：让整数类型匹配长度

传统循环用 `std::size_t index = 0;` 避免与 size() 的无符号结果混用。C++23 的 `0uz` 是 size_t 类型，`0z` 是 size_t 对应的有符号整数类型；不是固定的 64 位整数。

```cpp example id="cpp23-size-literal" std="c++23" file="main.cpp" kind="single" compilers="all" output="sum=6" requires="__cpp_size_t_suffix>=202011"
#include <cstddef>
#include <iostream>
#include <type_traits>
#include <vector>
int main() {
    static_assert(std::is_same_v<decltype(0uz), std::size_t>);
    static_assert(std::is_signed_v<decltype(0z)>);
    const std::vector<int> values{1, 2, 3};
    int sum = 0;
    for (auto index = 0uz; index < values.size(); ++index) sum += values[index];
    std::cout << "sum=" << sum << '\n';
}
```

不需要索引时仍优先范围循环。无符号类型不能表达负数，倒序循环必须另外处理下溢，`uz` 不会解决这个问题。

## 多参数 operator[]：二维访问不必绕到 operator()

过去自定义矩阵通常提供 `matrix(row, column)` 或返回行代理。C++23 可以直接声明两个参数的 operator[]，调用写作 `matrix[row, column]`。

```cpp example id="cpp23-multidimensional-subscript" std="c++23" file="main.cpp" kind="single" compilers="all" output="cell=7" requires="__cpp_multidimensional_subscript>=202110"
#include <array>
#include <cstddef>
#include <iostream>
struct Matrix {
    std::array<int, 6> data{};
    int& operator[](std::size_t row, std::size_t column) {
        return data.at(row * 3 + column);
    }
};
int main() {
    Matrix matrix;
    matrix[1, 2] = 7;
    std::cout << "cell=" << matrix[1, 2] << '\n';
}
```

本例只用合法坐标。at() 检查线性位置，不能代替分别检查 row < 2 与 column < 3；生产接口应按自己的形状验证。旧代码把 `object[a, b]` 当逗号表达式时，升级标准可能改变含义，应改成显式括号 `object[(a, b)]` 或重写。

## static operator() 与 static Lambda

普通无状态函数对象仍有隐式对象参数。C++23 允许静态调用运算符，也允许不捕获的 Lambda 使用 static。调用语法仍然是 function(args)。

```cpp example id="cpp23-static-call" std="c++23" file="main.cpp" kind="single" compilers="all" output="sum=5" requires="__cpp_static_call_operator>=202207"
#include <iostream>
int main() {
    auto add = [](int left, int right) static { return left + right; };
    std::cout << "sum=" << add(2, 3) << '\n';
}
```

适合无状态的函数对象接口。static Lambda 不能捕获变量，也不能与 mutable 或显式对象参数组合；需要捕获状态时使用普通 Lambda。它表达不依赖对象状态，不能据此承诺比普通无捕获 Lambda 更快。

## 权威资料

- [auto 的表达式用法](https://eel.is/c++draft/expr.type.conv)
- [整数后缀](https://eel.is/c++draft/lex.icon)、[下标运算符](https://eel.is/c++draft/over.sub)、[Lambda](https://eel.is/c++draft/expr.prim.lambda)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/language-improvements.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
