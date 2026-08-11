# 变量模板与放宽的 `constexpr`

变量模板为一族类型提供变量定义。C++14 的 `constexpr` 函数允许局部变量、循环和分支，使编译期算法更接近日常代码。

<!-- example id="cpp14-compile-time" std="c++14" file="main.cpp" kind="single" compilers="all" output="55" -->
```cpp
#include <iostream>
#include <type_traits>

template <typename T>
constexpr T zero = T{0};

constexpr int sum_to(int limit) {
    int result = 0;
    for (int value = 1; value <= limit; ++value) {
        result += value;
    }
    return result;
}

int main() {
    constexpr int result = sum_to(10) + zero<int>;
    static_assert(result == 55, "compile-time loop must work");
    static_assert(std::is_same<decltype(zero<long>), const long>::value,
                  "a constexpr variable is const");
    std::cout << result << '\n';
}
```

命名空间作用域的变量模板与普通模板一样可能涉及多翻译单元定义问题；C++17 的内联变量提供了更直接的处理方式。

## C++14 放宽了什么

C++11 常量函数几乎只能包含单个返回表达式，复杂算法被迫改写成递归。C++14 允许局部变量、条件、循环以及对局部对象的修改，只要常量求值路径仍不执行被禁止操作。这样编译期算法可以采用与运行期版本相同的迭代结构。

放宽语法不意味着所有标准库容器都能在编译期使用。C++14 标准库中的许多成员函数尚未标为 `constexpr`，动态分配也受到限制；通常使用字面类型、固定数组和纯计算。

## 变量模板实例化

变量模板为每组模板实参产生一个变量实例。`zero<int>` 与 `zero<double>` 是不同实体，具有各自类型和地址。示例把它声明为 `constexpr`，因此每个实例都是相应类型的常量值。

头文件中的非内联变量定义要遵守单一定义规则。常量模板的链接属性和取地址行为较细致，跨翻译单元共享身份时应设计清楚；C++17 `inline` 变量使头文件定义更直接。

## 常量求值引擎

编译器前端以解释器方式执行 `sum_to(10)` 的局部变量更新和循环，并在完成后产生常量 55。若改用运行期 `limit`，相同函数可以生成普通机器码。是否预计算由上下文决定，而不是由函数声明单独决定。

编译期循环过大同样会消耗构建时间，并可能触发编译器步数限制。把查表、协议常量等稳定计算前移通常有价值；把大型业务任务硬塞进常量求值则可能拖慢增量构建。

## 工程实践

- 为编译期算法同时测试边界值和运行期调用。
- 保持函数无外部状态、无未定义行为且输入规模可控。
- 变量模板名称应表达单位与类型语义，避免制造大量隐式全局状态。
- 用 `static_assert` 验证关键结果，但不要把实现细节写成难以演进的断言。

## 权威资料

- [N3652：放宽 constexpr](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3652.html)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
