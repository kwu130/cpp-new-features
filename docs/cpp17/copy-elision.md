# 保证的复制消除

C++17 在若干纯右值初始化场景中保证对象直接构造到最终存储位置，即使类型不能复制也不能移动，代码仍然合法。

<!-- example id="cpp17-copy-elision" std="c++17" file="main.cpp" kind="single" compilers="all" output="token=42" -->
```cpp
#include <iostream>

class Token {
public:
    explicit Token(int value) : value_(value) {}
    Token(const Token&) = delete;
    Token(Token&&) = delete;
    int value() const { return value_; }

private:
    int value_;
};

Token make_token() {
    return Token(42);
}

int main() {
    Token token = make_token();
    std::cout << "token=" << token.value() << '\n';
}
```

保证适用于直接返回同类型纯右值等规定场景；返回具名局部变量依赖 NRVO，仍不是语言强制保证。析构函数在相关上下文中仍必须可访问。

## C++17 纯右值模型

C++17 不只是“要求编译器做一次优化”，而是重新规定许多纯右值直到需要对象存储时才物化。`return Token(42)` 的纯右值直接初始化调用方结果对象，中间临时对象在抽象机中就不存在，因此类型可以删除复制和移动构造。

这与可选优化的“先创建临时再省略移动”不同。即使关闭常见优化，规定场景也必须合法。析构函数仍需在返回点可访问且未删除，因为语言要验证最终对象生命周期。

## 保证场景与 NRVO

同类型纯右值初始化目标对象、返回同类型纯右值等属于保证场景。具名返回值优化 NRVO 处理的是 `return local;`，局部变量是左值，标准仍允许但不强制省略。若 NRVO 未发生，编译器尝试移动，因此只移动类型通常仍可工作，但完全不可移动类型不能依赖 NRVO。

返回函数参数也不同于返回局部临时；参数已经是独立对象，不属于保证的直接构造目标。

## 生命周期和副作用

不应把复制/移动构造函数的可观察副作用作为业务逻辑。允许或保证的省略会改变这些函数是否执行。对象析构时间按相关规则选择较晚时点，但具体场景仍应以生命周期规则为准。

## 性能含义

按值返回大型对象可以直接构造到调用方存储，常与清晰所有权设计一致。它减少中间分配和搬迁，但对象内部是否分配仍由类型实现决定。为了“帮助优化”而手写 `std::move(local)` 可能阻止 NRVO。

## 示例解析与实践

示例的 `Token` 完全不可复制移动，却能从 `make_token` 返回，直接证明这里是语言保证。工程中优先按值返回拥有结果，避免返回局部引用；对 NRVO 场景保留简单 `return local;`，并让类型在合理时仍具备正确移动语义。
