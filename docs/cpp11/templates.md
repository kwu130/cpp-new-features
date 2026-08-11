# 可变参数模板与类型别名

可变参数模板允许模板接受任意数量的类型或值参数。别名模板用 `using` 为一族类型定义更易读的名称。

<!-- example id="cpp11-variadic-templates" std="c++11" file="main.cpp" kind="single" compilers="all" output="6" -->
```cpp
#include <iostream>
#include <memory>

template <typename T>
T sum(T value) {
    return value;
}

template <typename T, typename... Rest>
T sum(T first, Rest... rest) {
    return first + sum(rest...);
}

template <typename T>
using Owner = std::unique_ptr<T>;

int main() {
    Owner<int> result(new int(sum(1, 2, 3)));
    std::cout << *result << '\n';
}
```

C++11 中通常通过递归展开参数包，并提供终止重载。C++17 的折叠表达式会显著简化这种代码。参数包展开的上下文和求值顺序需要单独确认，不要假设函数实参按书写顺序求值。

## 参数包的组成

模板参数包 `typename... Types` 表示零个或多个模板参数，函数参数包 `Types... values` 表示由它们生成的一组函数参数。包本身不是运行期容器，不能索引；只有在带省略号的模式中才能展开。

若 `Types` 是 `int, double, string`，模式 `const Types&...` 会展开为三个独立参数。`sizeof...(Types)` 在编译期返回元素数量，不会生成遍历代码。

## 实例化模型

模板在使用点以具体实参实例化。主示例的 `sum(1, 2, 3)` 会形成多个不同签名的 `sum` 实例，每层处理一个参数并调用参数更少的实例，直到匹配单参数终止重载。优化器通常能内联这些层次，但模板实例数量仍会增加编译时间和目标文件体积。

包展开只是语法生成，求值顺序由展开所在语法决定。C++11 函数实参之间没有固定求值顺序；若展开项带副作用，应使用具有明确顺序的结构，或先消除副作用。

## 别名模板为何重要

传统 `typedef` 不能直接参数化，常需要额外包装结构体。`using Alias = ...` 的右侧从左到右更接近普通赋值写法，并能定义别名模板。别名不会创建新类型；`Owner<int>` 与 `std::unique_ptr<int>` 完全是同一类型，重载系统无法区分它们。

## 递归边界与诊断

可变参数递归必须有可匹配终止条件，否则实例化会不断继续并产生很深的错误信息。还应考虑空参数包是否有业务含义：求和可选择返回单位元，也可通过约束禁止空调用。

## 工程实践

- 把复杂包展开封装在小型辅助函数中，公共接口保持直观。
- 对参数数量、类型关系用 `static_assert` 提前给出清晰诊断。
- 使用转发引用时才配合 `std::forward<Types>(values)...`。
- 关注编译时间和代码膨胀；对大量类型共享的逻辑移到非模板实现中。

## 有序展开参数包

C++11 函数实参求值顺序不能用于实现有副作用的左到右遍历。常见方案是把每一步放进初始化列表，因为初始化器元素按顺序求值。额外的首元素保证空参数包时数组仍有合法长度。

<!-- example id="cpp11-ordered-pack-expansion" std="c++11" file="main.cpp" kind="single" compilers="all" output="1 2 3" -->
```cpp
#include <iostream>

template <typename... Values>
void print_in_order(const Values&... values) {
    bool first = true;
    using Expansion = int[];
    (void)Expansion{0, ((std::cout << (first ? "" : " ") << values,
                         first = false), 0)...};
    std::cout << '\n';
}

int main() {
    print_in_order(1, 2, 3);
}
```

这个技巧依赖初始化列表的顺序保证，而不是依赖编译器碰巧从左到右计算函数参数。C++17 的逗号折叠表达式能更直接表达同一意图。

## 别名不是强类型

`using UserId = int` 只提供另一个拼写，不能阻止把订单编号传给用户编号接口。需要真正区分领域值时，应定义包装结构体并显式提供比较、哈希与转换。别名模板适合简化类型组合，不适合建立新的类型安全边界。

## 权威资料

- [可变参数模板](https://eel.is/c++draft/temp.variadic)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
