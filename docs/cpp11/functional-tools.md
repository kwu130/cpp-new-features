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

`make_tuple(args...)` 推导并通常衰减元素类型，`tie(args...)` 生成左值引用 tuple，`forward_as_tuple(args...)` 保存转发引用。三者所有权和生命周期完全不同，不能因都返回 tuple 就互换。

make_tuple 对 `reference_wrapper<T>` 有特殊处理，可得到 T& 元素；普通变量默认复制/移动成值。需要精确类型时可直接写 tuple<T...> 构造。forward_as_tuple 常用于立即转发构造，保存它会让临时引用悬空。

tuple 支持字典序关系比较，前提是元素对应比较有效；比较顺序按索引。`tuple_cat` 拼接多个 tuple-like 对象并构造新 tuple，可能复制/移动元素，值类别和引用元素要审查。

### 赋值与引用 tuple

tuple 赋值逐元素执行，tie 正是利用引用元素把右侧多值写入已有变量。若右侧求值产生临时，赋值在完整表达式内完成通常安全；把 tie 结果长期保存则依赖所有引用对象寿命。

`std::ignore` 是可接收赋值的占位对象，用于丢弃某些结果。它不让被忽略结果免于构造，函数仍先产生完整 tuple；若计算昂贵，API 应支持选择字段而不是只在解包时 ignore。

## 类型萃取与编译期分派

类型萃取是带静态成员或嵌套类型的模板。`is_integral<T>::value` 在编译期产生布尔值，`remove_reference<T>::type` 产生转换后的类型。C++11 常配合 SFINAE 和 `enable_if` 选择重载，但错误信息可能复杂；C++20 Concepts 将提供更直接的约束表达。

萃取只描述语言可判断的类型性质，不能替代业务语义。例如“可复制”不代表复制廉价，“算术类型”也不表示适合所有数学算法。

C++11 萃取大致分为查询型（is_*）、关系型（is_same/is_base_of/is_convertible）、属性型（alignment_of/rank/extent）和变换型（remove_*/add_*/decay/common_type）。查询通常继承 integral_constant，变换通过嵌套 `type` 返回结果。

模板推导得到 T&/const T 时，直接 `is_integral<T>` 可能为 false；是否先 remove_reference/remove_cv 取决于接口语义。机械 decay 会把数组变指针、函数变函数指针，也可能丢失需要的边界信息。

`is_trivially_*`、`is_standard_layout` 等描述语言类别，可用于优化 memcpy/ABI 互操作，但必须满足每个操作的完整前置条件。trivially copyable 也不意味着对象表示跨平台稳定。

用户只能在标准允许范围特化某些模板；随意特化标准类型萃取通常导致未定义行为。领域能力应定义自己的 trait，并给用户类型提供明确扩展点。

## `std::function` 的类型擦除

`std::function<R(Args...)>` 可以保存函数指针、Lambda、函数对象或 `bind` 结果。实现通常在对象内保存一组擦除后的调用/复制/销毁操作指针，并使用小对象缓冲区避免部分堆分配。调用经过间接层，空对象调用会抛 `bad_function_call`。

类型擦除要求目标可复制，这会排除只移动闭包。若调用方是模板且无需异构存储，直接接收可调用对象能保留内联机会；若需要稳定 ABI、运行期替换或同一容器存放不同回调，`std::function` 更合适。

默认构造或赋 nullptr 产生空 function，显式 bool 检查是否有目标；调用空对象抛 bad_function_call。把空回调作为“无监听者”很常见，但实时/无异常代码应先检查而不是依赖抛出。

`target_type()` 返回存储目标的 type_info，`target<T>()` 在精确类型匹配时返回指针。它们不做基类/可转换匹配，依赖具体闭包类型进行业务分派通常破坏类型擦除目的。

小对象优化阈值不标准化。函数指针/reference_wrapper 等有相应无分配保证边界，任意小闭包是否堆分配要测目标实现。std::function 自身复制会复制目标，目标抛异常时传播。

函数签名 R(Args...) 会对实参/返回值做普通转换。包装返回引用的目标时，必须确保引用寿命；void 签名可丢弃底层非 void 结果。签名没有 noexcept 维度（在 C++11），也不表达一次性调用。

## `bind` 的参数绑定

`bind` 创建一个保存函数和绑定参数的函数对象，占位符决定调用时参数插入位置。默认会复制绑定值；要绑定引用必须使用 `std::ref`。嵌套 `bind` 和重载函数常导致类型推导难读，现代代码优先使用 Lambda 明确写出捕获与调用。

<!-- example id="cpp11-bind-reference" std="c++11" file="main.cpp" kind="single" compilers="all" output="value=42" -->
```cpp
#include <functional>
#include <iostream>

void add_to(int& value, int amount) {
    value += amount;
}

int main() {
    int value = 40;
    const std::function<void(int)> add =
        std::bind(add_to, std::ref(value), std::placeholders::_1);
    add(2);
    std::cout << "value=" << value << '\n';
}
```

如果去掉 std::ref，bind 对象保存 value 副本，add_to 修改的是内部副本而非外围变量。`std::cref` 保存 const 引用包装，适合只读绑定。两者都不拥有对象，绑定对象必须活得足够久。

占位符 `_1` 等来自 std::placeholders，表示调用 bind 结果时第几个实参。重复占位符可能多次转发同一实参；若它是右值/有副作用对象，语义容易复杂。未使用的额外调用实参仍会求值后被丢弃。

绑定普通值在创建 bind 对象时 decay-copy，调用时通常以左值成员传给目标；想在调用时每次移动某绑定对象很难直观表达。Lambda/命名函数对象更适合精确控制 move 和 const 重载。

重载函数名传给 bind 时需要显式 cast 或函数指针变量选择签名，成员函数指针还要绑定对象/指针/reference_wrapper。`mem_fn` 可把成员指针转换为统一函数对象，通常比复杂 bind 更轻量可读。

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

若函数只在当前调用栈使用回调，模板参数或函数引用避免拥有/分配；若要长期保存多种可复制目标，用 std::function；若只接受 C 回调，用函数指针加 void* 上下文；若要求 move-only，C++11 需自定义擦除或命名任务类型。

稳定 ABI 的 std::function 仍依赖双方标准库 ABI/编译选项，跨编译器插件边界不等于 C ABI。公共二进制接口常用纯虚接口或 C 函数表，并在内部转换。

## 调用工具速查

| 设施 | 关键语义 |
| --- | --- |
| `tuple<Ts...>` | 固定长度异构积类型，索引在编译期 |
| `get<I>` | 按索引访问并保留相应引用类别 |
| `get<T>` | 按类型访问是后续标准增强，勿写入最低 C++11 示例 |
| `tie` | 建立引用 tuple，常用于解包和字典序比较 |
| `ignore` | tie 赋值时丢弃某个位置 |
| `tuple_size` | 编译期元素数量协议 |
| `function<R(Args...)>` | 拥有可复制调用目标的类型擦除包装 |
| 空 `function` 调用 | 抛 `bad_function_call` |
| `bind` | 保存可调用对象/参数，placeholder 在调用时替换 |
| `ref` / `cref` | 在按值包装协议中显式保留引用语义 |
| `mem_fn` | 把成员指针适配为统一可调用对象 |
| 类型萃取 | 多数暴露 `value`/`type`，C++14 才普及 `_t` 简写 |

## 函数工具专项审查

- tuple 索引是否在编译期范围内并与字段语义一致？
- tie 返回引用是否越过被绑定对象寿命？
- function 目标是否满足 C++11 可复制要求？
- 空 function 是否可能被调用并抛 bad_function_call？
- 类型擦除分配和虚调用成本是否位于热路径？
- bind 默认按值保存参数是否符合生命周期/状态意图？
- 需要引用时是否显式使用 ref/cref？
- placeholder 顺序是否让公共调用签名难以理解？
- 成员指针目标对象是否持续存活？
- traits 的 `type`/`value` 错误是否处于正确 SFINAE 语境？

## 权威资料

- [函数对象与调用包装](https://eel.is/c++draft/function.objects)
- [CPP11 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2012/n3337.pdf)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
