# 泛型 Lambda 与初始化捕获

泛型 Lambda 可以用 `auto` 声明参数，本质上生成带模板调用运算符的闭包。初始化捕获允许在捕获列表中创建成员，尤其适合把只移动对象交给回调。

<!-- example id="cpp14-lambdas" std="c++14" file="main.cpp" kind="single" compilers="all" output="42" -->
```cpp
#include <iostream>
#include <memory>

int main() {
    auto add = [](const auto& left, const auto& right) { return left + right; };
    std::unique_ptr<int> value(new int(40));
    auto calculate = [owned = std::move(value), add]() {
        return add(*owned, 2);
    };

    std::cout << calculate() << '\n';
}
```

初始化捕获的名称属于闭包对象，而不属于外围作用域。移动捕获会使闭包通常只能移动；若把它放入要求可复制目标的 C++14 `std::function`，会发生编译错误。

## 泛型 Lambda 的转换模型

C++11 Lambda 的参数类型固定，想对不同数值类型复用逻辑需要单独定义函数对象模板。C++14 允许参数写 `auto`，编译器把闭包的 `operator()` 生成为成员函数模板。每一种实参类型仍会产生独立实例，调用保持静态分派，并非把参数装进运行期“万能类型”。

多个 `auto` 参数彼此独立推导；若业务要求两者类型相同，C++14 只能在函数体中用 `static_assert` 检查，C++20 才能更自然地写 Concepts 约束。泛型 Lambda 同样参与模板实例化，错误信息、代码膨胀和隐式转换规则都应按模板代码理解。

## 初始化捕获的对象模型

`[name = expression]` 在闭包对象中创建一个由表达式初始化的成员，其类型由 `auto` 规则推导。外围作用域不需要存在同名变量。示例中的 `owned = std::move(value)` 把 `unique_ptr` 移入闭包，原指针随后为空。

闭包因此包含只移动成员，编译器隐式生成的复制构造被删除。把这种闭包交给线程通常可移动，但 C++14 `std::function` 要求目标可复制，不能直接保存。接口设计应明确回调需要复制、移动还是仅在调用期间借用。

初始化捕获还可用于规范化类型、预计算值或只捕获对象的某个成员，而不是整个 `this`。但表达式只在创建闭包时求值一次，不能把它误解成每次调用重新计算。

## 生命周期与并发

按引用初始化捕获仍不拥有对象；例如 `[&alias = object]` 只是闭包中的引用语义。异步执行前必须保证对象生命周期覆盖任务。按值捕获可减少悬空风险，但闭包副本之间各有状态；若多个副本需要共享同步状态，应显式捕获共享对象并设计线程安全。

## 示例解析与实践

示例的 `add` 会为整数调用实例化对应调用运算符，`calculate` 则拥有原 `unique_ptr`。两层 Lambda 都可被内联，通常没有动态分配。代码审查时检查泛型参数是否过宽、捕获表达式是否有副作用、闭包是否需要复制，以及移动后的外围对象是否仍被误用。

## 同一闭包的多次模板实例化

泛型 Lambda 的闭包类型只有一个，但它的调用运算符是模板。用不同参数类型调用时，编译器分别推导并实例化 `operator()`。这与一个函数模板被多种类型调用的代码尺寸和重载行为相同。

返回类型仍由每次实例化单独推导，因此某个参数组合合法不代表所有组合都合法。操作符 `+` 对整数表示算术，对字符串表示拼接；Concepts 出现前，泛型 Lambda 很难在声明处直接表达这种语义约束。

<!-- example id="cpp14-generic-lambda-instances" std="c++14" file="main.cpp" kind="single" compilers="all" output="sum=42, text=cpp14" -->
```cpp
#include <iostream>
#include <string>

int main() {
    const auto combine = [](const auto& left, const auto& right) {
        return left + right;
    };

    const int sum = combine(20, 22);
    const std::string text = combine(std::string("cpp"), std::string("14"));
    std::cout << "sum=" << sum << ", text=" << text << '\n';
}
```

## `mutable` 与移动捕获

移动捕获只发生在闭包构造时。闭包的调用运算符默认 `const`，若要从捕获的 `unique_ptr` 再次转移所有权，需要 `mutable`。这种回调往往只能成功消费一次，接口必须说明重复调用后的行为。

异步 API 如果复制回调，会拒绝只移动闭包或改变消费语义。C++14 项目常让任务队列自身支持移动任务，而不是强制套进可复制的 `std::function`。

## 权威资料

- [N3649：泛型 Lambda](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2013/n3649.html)
- [CPP14 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2018/p1319r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
