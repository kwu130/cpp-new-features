# 显式对象参数：把调用对象纳入推导

阅读前建议先了解：[引用与值类别](../prerequisites.md#值类别先区分表达式的用途)、[完美转发](../cpp11/move-semantics.md#完美转发与引用折叠)。本篇介绍的新增能力属于 C++23。

## 为什么需要它

类经常同时提供可修改和只读访问器。传统成员函数通过隐式 this 访问对象，const 重载和非 const 重载往往重复一份代码。C++23 可以把调用对象写成首个参数，让模板推导决定它的类型；常称为 deducing this。

先解决 const 与非 const 两份实现的问题，稍后再处理右值。传统写法如下，片段不作为独立程序运行：

```text
int& get() & { return value; }
const int& get() const & { return value; }
```

## 先认识语法：给调用对象起一个名字

普通成员函数中的 `this` 隐式指向调用对象。下面先把对象写成显式的只读引用参数，观察调用方式：

```cpp example id="cpp23-explicit-object-basic" std="c++23" file="main.cpp" kind="single" compilers="all" output="value=3" requires="__cpp_explicit_this_parameter>=202110"
#include <iostream>
struct Box {
    int value = 3;
    int get(this const Box& self) {
        return self.value;
    }
};
int main() {
    const Box box;
    std::cout << "value=" << box.get() << '\n';
}
```

`this const Box& self` 表示“将调用对象作为名为 self 的只读引用”。调用仍写 `box.get()`，不手动传 box；函数体用 `self.value` 访问成员。本例按值返回 int，与普通 `int get() const` 的读取行为相同，还没有用到模板推导。

接下来才让 `self` 的类型由编译器推导，从而减少重复重载。

## 进一步使用：同一个成员实现，两种引用

```cpp example id="cpp23-explicit-object" std="c++23" file="main.cpp" kind="single" compilers="all" output="value=7" requires="__cpp_explicit_this_parameter>=202110"
#include <iostream>
#include <type_traits>
struct Box {
    int value = 3;
    template <typename Self>
    decltype(auto) get(this Self& self) {
        return (self.value);
    }
};
int main() {
    Box box;
    const Box& read_only = box;
    static_assert(std::is_same_v<decltype(box.get()), int&>);
    static_assert(std::is_same_v<decltype(read_only.get()), const int&>);
    box.get() = 7;
    std::cout << "value=" << read_only.get() << '\n';
}
```

调用仍是 box.get()，不需要手动传 self。Self 对可修改对象推导为 Box，对只读对象推导为 const Box；Self& 让这里的接口只接受左值。返回值的括号使 decltype(auto) 按表达式推导引用；去掉括号会按成员声明类型推导，变成按值返回。

## 进一步理解：推导调用对象

显式对象参数必须放在首位，用 this 标记；它不能有默认实参。函数体通过 self 访问成员，不能再使用隐式 this。显式对象成员不能是 static 或 virtual，也不能在函数末尾另加 const、&、&& 限定符；限定体现在参数类型中。

若写成 `this Self&& self`，则成为转发引用，可以覆盖 const/非 const、左值/右值组合。实现中常借助 [forward_like](utility-and-bit.md#forward_like按另一个类型的性质转发) 转发成员，但返回临时对象内部的引用仍会悬空。入门例故意只接受左值，避免让读者把消除重载理解为自动管理生命周期。

显式对象参数也可按值接收调用对象，那会复制或移动对象；不是所有形式都只是引用绑定。取得这类成员函数地址得到普通函数指针，调用时显式传入对象；与传统成员函数指针的调用协议不同。

## 场景与陷阱

适合需要统一 cv/ref 访问器、泛型混入或递归 Lambda 的接口。少量不重复的普通成员函数保持原写法更清楚。公开泛型 Self 接口时仍要核对可接受对象及返回类型；过宽的推导可能把未预料的派生类型行为纳入实现。

```text
Box{}.get(); // 本例拒绝右值调用，防止轻易取得临时 Box 的成员引用
```

它没有改变访问控制、对象寿命或虚函数机制。C++23 的语法支持由编译器决定，不能仅用标准库版本推断。

## 权威资料

- [显式对象成员函数](https://eel.is/c++draft/dcl.fct)
- [P0847R7：Deducing this](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2021/p0847r7.html)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/explicit-object-parameter.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
