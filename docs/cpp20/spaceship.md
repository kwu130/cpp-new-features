# 三路比较运算符

`<=>` 一次表达小于、等于和大于关系。编译器可据此重写常见比较表达式，并为成员逐项生成一致的默认比较。

<!-- example id="cpp20-spaceship" std="c++20" file="main.cpp" kind="single" compilers="all" output="older=true, same=true" -->
```cpp
#include <compare>
#include <iostream>
#include <string>

struct Version {
    int major;
    int minor;
    auto operator<=>(const Version&) const = default;
};

int main() {
    const Version current{2, 1};
    const Version previous{1, 9};
    std::cout << std::boolalpha
              << "older=" << (previous < current)
              << ", same=" << (current == Version{2, 1}) << '\n';
}
```

默认比较按成员声明顺序进行。浮点成员可能使结果成为偏序，因为 NaN 不与任何值有序；自定义比较类别必须符合类型真实语义。

## 比较类别

三路比较不简单返回 -1/0/1，而返回比较类别对象。`strong_ordering` 表示可替代的全序，`weak_ordering` 允许等价但不可替代的值，`partial_ordering` 允许无序结果。浮点比较因 NaN 通常是偏序。

调用方通常写 `a < b`、`a == b`，编译器把关系表达式改写为 `<=>` 和必要的 `==`。不要依赖比较类别对象的内部整数表示，应与零比较或使用命名结果。

## 默认成员比较

`= default` 按基类和非静态成员的声明顺序逐项比较，遇到非相等结果即停止。编译器从成员比较能力推导返回类别；若某成员不可比较，默认运算符会被删除。

默认 `<=>` 同时可促成生成相等比较，但自定义 `<=>` 时通常还要明确 `operator==`。对指针、浮点、大小写不敏感字符串等成员，应确认默认语义真的是业务需要。

## 排序一致性

关联容器和排序算法依赖严格弱序。自定义比较若违反传递性，容器行为会失去保证。相等、哈希和排序也应保持一致：若两个对象业务上等价，哈希键和比较策略必须采用同一规范化规则。

## 性能与迁移

默认比较可被内联成与手写逐成员比较相当的代码，并减少六个关系运算符不一致。迁移旧类时先写测试覆盖所有关系和边界，尤其是浮点 NaN、忽略大小写、版本预发布标签和不参与身份的缓存字段。

## 示例解析

`Version` 两个整数形成强序，先比较 major，再比较 minor。编译器据默认 `<=>` 支持 `<`，并生成一致的 `==`。若增加构建时间戳成员，默认顺序会立刻纳入它，代码审查必须确认这是否属于版本身份。

## 权威资料

- [P0515R3：三路比较](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2017/p0515r3.pdf)
- [CPP20 版本变化或工作草案总览](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2020/p2131r0.html)

提案用于理解设计动机和最初采用的方案；规范性行为应以对应标准版本和后续缺陷修正后的工作草案为准。
