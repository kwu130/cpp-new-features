# move_only_function：保存不可复制的回调

阅读前建议先了解：[独占所有权](../cpp11/smart-pointers.md)、[Lambda 捕获](../cpp14/lambdas.md)、[std::function](../cpp11/functional-tools.md)。本篇介绍的新增能力属于 C++23。

## 传统包装器的限制

std::function 要求保存的目标可复制。一个 Lambda 如果按值捕获 unique_ptr，就不能复制，因而不能直接交给 std::function。过去需要改成共享所有权、设计专用任务对象，或使用自己的包装器。

C++23 的 move_only_function 进行类型擦除：调用方只看到签名，不需知道回调具体类型。包装器自身可移动、不可复制，适合队列里唯一拥有任务的情况。它不会把 unique_ptr 改成 shared_ptr。

## 最小示例：转交一个独占回调

```cpp example id="cpp23-move-only-function" std="c++23" file="main.cpp" kind="single" compilers="all" output="value=42" requires="__cpp_lib_move_only_function>=202110"
#include <cassert>
#include <functional>
#include <iostream>
#include <memory>
#include <utility>
int main() {
    std::move_only_function<int()> task =
        [value = std::make_unique<int>(42)] { return *value; };
    auto receiver = std::move(task);
    assert(receiver);
    std::cout << "value=" << receiver() << '\n';
}
```

unique_ptr 被转交给闭包对象，闭包再被包装器拥有，receiver 接管包装器。只调用已确认有目标的 receiver，不假定源包装器移动后的内容。与为了满足可复制性而改用 shared_ptr 的做法相比，所有权模型更贴近这个任务；并不保证无分配。

旧包装器拒绝的代码如下：

```text
std::function<int()> task = [p = std::make_unique<int>(42)] { return *p; };
// 目标不可复制，不满足 std::function 要求
```

## 签名可以表达调用限制

move_only_function 支持 const、引用限定符及 noexcept 签名。例如 `move_only_function<void() &&>` 表达通过右值包装器调用；这不会自动令任务只能调用一次，是否消耗状态仍由目标实现决定。

它不提供 std::function 的 target_type()/target<T>() 检查接口。包装器不应被当成对象类型注册表。

## 注意事项与成本

空包装器的调用违反前置条件；它没有 std::function 空调用抛 bad_function_call 的保证。先检查 bool，再调用；也不能把 noexcept 签名理解为调用时会兜底捕获异常，目标必须满足相应不抛要求。

捕获引用时，包装器不会延长外部对象寿命。并发调用同一可变闭包仍可能产生数据竞争。内部可采用小对象存储或动态分配，但阈值与布局由实现决定，必须测量真实任务。

可复制回调确实需要多份时继续使用 std::function；回调类型在编译期已知时，普通模板参数或直接 Lambda 能省去类型擦除层。C++26 的 function_ref、copyable_function 不属于 C++23。

## 权威资料

- [move_only_function](https://eel.is/c++draft/func.wrap.move)
- [P0288R9](https://www.open-std.org/jtc1/sc22/wg21/docs/papers/2021/p0288r9.html)

## 运行本篇示例

从仓库根目录运行；源码就是本文的完整 `cpp` 围栏：

```shell
python3 tools/verify_examples.py --compiler clang++ --path docs/cpp23/move-only-function.md
```

带 `requires` 元数据的示例按特性测试宏检查支持程度；缺少能力时报告跳过及原因，跳过不代表通过。使用真正的 GCC 时将 `clang++` 替换为 `g++`。

[返回 C++23 入口](README.md)
