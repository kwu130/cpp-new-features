# `tuple`、类型萃取与可调用对象

`tuple` 表示固定数量的异构值；类型萃取支持编译期类型查询与转换；`function` 提供统一的类型擦除调用接口。

<!-- example id="cpp11-functional-tools" std="c++11" file="main.cpp" kind="single" compilers="all" output="Ada:42" -->
```cpp
#include <functional>
#include <iostream>
#include <string>
#include <tuple>
#include <type_traits>

std::string describe(const std::string& name, int score) {
    return name + ':' + std::to_string(score);
}

int main() {
    typedef std::tuple<std::string, int> Record;
    Record record("Ada", 42);
    static_assert(std::tuple_size<Record>::value == 2, "Record has two fields");
    static_assert(std::is_integral<std::tuple_element<1, Record>::type>::value,
                  "the score is integral");

    std::function<std::string(const std::string&)> formatter =
        std::bind(describe, std::placeholders::_1, std::get<1>(record));
    std::cout << formatter(std::get<0>(record)) << '\n';
}
```

`std::function` 可能产生分配和间接调用开销；无需存储异构可调用对象时优先使用模板或具体 Lambda 类型。新代码中 Lambda 通常比复杂的 `bind` 表达式更直观。

## `tuple` 的结构与访问

`tuple<Ts...>` 是固定长度异构乘积类型，元素类型和数量都在编译期确定。典型实现通过递归继承或索引化叶子类型存储成员，并对空类型应用空基类优化；标准只保证可观察行为，不保证布局顺序或紧凑程度。

`get<I>` 按索引访问，`tuple_element` 和 `tuple_size` 在编译期查询结构。索引错误是编译错误而非运行期异常。大量位置索引会降低可读性，业务数据通常更适合具名结构体；元组更适合局部组合、泛型适配和多值返回。

## 类型萃取与编译期分派

类型萃取是带静态成员或嵌套类型的模板。`is_integral<T>::value` 在编译期产生布尔值，`remove_reference<T>::type` 产生转换后的类型。C++11 常配合 SFINAE 和 `enable_if` 选择重载，但错误信息可能复杂；C++20 Concepts 将提供更直接的约束表达。

萃取只描述语言可判断的类型性质，不能替代业务语义。例如“可复制”不代表复制廉价，“算术类型”也不表示适合所有数学算法。

## `std::function` 的类型擦除

`std::function<R(Args...)>` 可以保存函数指针、Lambda、函数对象或 `bind` 结果。实现通常在对象内保存一组擦除后的调用/复制/销毁操作指针，并使用小对象缓冲区避免部分堆分配。调用经过间接层，空对象调用会抛 `bad_function_call`。

类型擦除要求目标可复制，这会排除只移动闭包。若调用方是模板且无需异构存储，直接接收可调用对象能保留内联机会；若需要稳定 ABI、运行期替换或同一容器存放不同回调，`std::function` 更合适。

## `bind` 的参数绑定

`bind` 创建一个保存函数和绑定参数的函数对象，占位符决定调用时参数插入位置。默认会复制绑定值；要绑定引用必须使用 `std::ref`。嵌套 `bind` 和重载函数常导致类型推导难读，现代代码优先使用 Lambda 明确写出捕获与调用。

## 工程检查清单

业务记录优先具名结构体；泛型元数据使用类型萃取；高频调用避免不必要类型擦除；长期回调审查捕获生命周期；任何 `bind` 表达式若不能一眼看懂，改写为 Lambda。

## 使用类型萃取选择接口

`enable_if` 根据编译期布尔条件是否存在成员 `type`，利用替换失败从候选集合移除函数模板。它适合 C++11 库实现兼容性，但条件出现在返回类型时可能让诊断难读；应把约束封装成有名称的萃取。

<!-- example id="cpp11-type-traits-dispatch" std="c++11" file="main.cpp" kind="single" compilers="all" output="integer floating" -->
```cpp
#include <iostream>
#include <type_traits>

template <typename T>
typename std::enable_if<std::is_integral<T>::value, const char*>::type
category(T) {
    return "integer";
}

template <typename T>
typename std::enable_if<std::is_floating_point<T>::value, const char*>::type
category(T) {
    return "floating";
}

int main() {
    std::cout << category(42) << ' ' << category(3.5) << '\n';
}
```

两个模板的函数签名不能只依赖默认模板实参差异，否则可能被视为重复声明。真实库还要处理枚举、用户数值类型和 cv/ref 限定，不能简单把标准算术类型等同于业务可计算类型。

## `tie`、`ignore` 与元组赋值

`std::tie` 创建引用元组，可把多值结果解包到已有变量；`std::ignore` 丢弃不关心的位置。引用元组不拥有对象，不能保存到超过被引用变量寿命的地方。C++17 结构化绑定通常更适合声明新变量，而 `tie` 仍适合给已有变量赋值。

## 类型擦除的接口选择

`std::function` 的签名只描述参数和返回值，不表达 `noexcept`、所有权或调用次数。回调注册接口还需在文档中说明是否复制、在哪个线程调用、能否重入、保存多久以及异常如何处理。类型擦除解决存储问题，不自动补足这些契约。

## 权威资料

- [函数对象与调用包装](https://eel.is/c++draft/function.objects)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
