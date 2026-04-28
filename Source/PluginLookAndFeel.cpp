/*
    This code is part of the Supertonal guitar effects multi-processor.
    Copyright (C) 2023-2024  Paul Jones

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>
*/

#include "PluginLookAndFeel.h"
#include <cmath>

// ================= 主题色集中管理 =================
namespace UITheme
{
    // 背景 / 面板
    static const juce::Colour surfaceBg = juce::Colour::fromRGB(0xF4, 0xF8, 0xFA);
    static const juce::Colour panelBg = juce::Colour::fromRGB(0xE9, 0xF1, 0xF5);

    // 控件基底（旋钮底、普通按钮）
    static const juce::Colour controlBase = juce::Colour::fromRGB(0xDF, 0xE7, 0xEC);
    static const juce::Colour controlBaseHi = juce::Colour::fromRGB(0xE7, 0xF0, 0xF4); // 轻高光

    // 轨道 / 分隔
    static const juce::Colour trackBg = juce::Colour::fromRGB(0xC7, 0xD5, 0xDD);
    static const juce::Colour trackBgSubtle = juce::Colour::fromRGB(0xD5, 0xE1, 0xE7);

    // 强调色（主色系：柔和蓝灰）
    static const juce::Colour accentBase = juce::Colour::fromRGB(0x4F, 0x6B, 0x7A);
    static const juce::Colour accentHover = juce::Colour::fromRGB(0x3F, 0x5E, 0x6D);
    static const juce::Colour accentActive = juce::Colour::fromRGB(0x2F, 0x4E, 0x5B);
    static const juce::Colour accentBright = juce::Colour::fromRGB(0x2F, 0x80, 0xA8); // 选中/突显
    static const juce::Colour accentDisabled = juce::Colour::fromRGB(0xA9, 0xBC, 0xC5);

    // 文字
    static const juce::Colour textMain = juce::Colour::fromRGB(0x22, 0x32, 0x3A);
    static const juce::Colour textSubtle = juce::Colour::fromRGB(0x5A, 0x6B, 0x73);
    static const juce::Colour textDisabled = juce::Colour::fromRGB(0x88, 0x98, 0xA2);

    // 边框 / 阴影 / 焦点
    static const juce::Colour borderSoft = juce::Colour::fromRGB(0xC4, 0xD2, 0xDA);
    static const juce::Colour focusRing = juce::Colour::fromRGB(0x66, 0xB8, 0xFF);

    // 渐变点（可用于旋钮帽子）
    static const juce::Colour capHighlight = juce::Colour::fromRGB(0xFA, 0xFC, 0xFD);
    static const juce::Colour capShade = juce::Colour::fromRGB(0xD9, 0xE3, 0xE8);

    static const juce::Colour comboPlaceholder = juce::Colour::fromRGB(0x64, 0x64, 0x64);
}

// ================= 构造函数（可选） =================
PluginLookAndFeel::PluginLookAndFeel()
{
    // 可在此设置全局默认字体或其他 LookAndFeel_V4 配置
    setColour(juce::PopupMenu::backgroundColourId, UITheme::panelBg);
    setColour(juce::PopupMenu::highlightedBackgroundColourId, UITheme::accentBase.withAlpha(0.15f));
    setColour(juce::PopupMenu::textColourId, UITheme::textMain);
}

PluginLookAndFeel::~PluginLookAndFeel() = default;

// ================= 工具函数（可选） =================
static juce::Font getKnobLabelFont()
{
    return juce::Font(12.0f, juce::Font::plain);
}

static bool isPrimaryButton(const juce::Button& b)
{
    // 你可以通过设置 ID / component name 来标记主按钮
    // 例如：button.setComponentID("primary");
    return b.getComponentID() == "primary";
}

// ================= 旋钮绘制 =================
void PluginLookAndFeel::drawRotarySlider(juce::Graphics& g,
    int x, int y, int width, int height,
    float sliderPosProportional,
    const float rotaryStartAngle,
    const float rotaryEndAngle,
    juce::Slider& slider)
{
    auto bounds = juce::Rectangle<int>(x, y, width, height).toFloat().reduced(6.0f);
    auto centre = bounds.getCentre();
    float radius = juce::jmin(bounds.getWidth(), bounds.getHeight()) / 2.0f;

    // 绘制外围刻度文本 (如果尺寸足够)
    const bool showTicks = radius > 60.0f;
    const int tickTextH = 12;
    const int sideTextWidth = 42;

    g.setFont(getKnobLabelFont());
    g.setColour(slider.isEnabled() ? UITheme::textSubtle : UITheme::textDisabled);

    if (showTicks)
    {
        // 预留顶部区域
        auto labelArea = bounds;
        labelArea.removeFromTop(2);

        auto left = int(bounds.getX());
        auto right = int(bounds.getRight() - sideTextWidth);
        auto top = int(bounds.getY());
        auto bottom = int(bounds.getBottom() - tickTextH);

        // 采用 0, 0.125, ..., 1.0 这些点（与原逻辑类似）
        struct Tick { float p; juce::Justification just; int x; int y; };
        std::vector<Tick> ticks;

        auto mapY = [&](float norm) -> int
            {
                return int(juce::jmap(norm, float(top), float(bottom)));
            };

        ticks.push_back({ 0.50f, juce::Justification::centred, int(centre.x - sideTextWidth / 2), top });
        ticks.push_back({ 0.375f, juce::Justification::left, left, top });
        ticks.push_back({ 0.25f, juce::Justification::left, left, mapY(0.33f) });
        ticks.push_back({ 0.125f, juce::Justification::left, left, mapY(0.66f) });
        ticks.push_back({ 0.0f, juce::Justification::left, left, bottom });
        ticks.push_back({ 0.625f, juce::Justification::right, right, top });
        ticks.push_back({ 0.75f, juce::Justification::right, right, mapY(0.33f) });
        ticks.push_back({ 0.875f, juce::Justification::right, right, mapY(0.66f) });
        ticks.push_back({ 1.0f, juce::Justification::right, right, bottom });

        for (auto& t : ticks)
        {
            auto value = slider.proportionOfLengthToValue(t.p);
            auto text = slider.getTextFromValue(value);
            g.drawFittedText(text, t.x, t.y, sideTextWidth, tickTextH, t.just, 1);
        }

        // 收紧 bounds 留出文字空间
        bounds.removeFromTop(tickTextH + 4.0f);
        bounds.reduce((float)sideTextWidth, 0.0f);

        // 重新计算中心和半径
        radius = juce::jmin(bounds.getWidth(), bounds.getHeight()) / 2.0f;
        centre = bounds.getCentre();
    }

    // 轨道参数
    const float lineW = juce::jlimit(2.0f, 5.0f, radius * 0.12f);
    const float arcRadius = radius - lineW * 0.8f;

    // 背景轨道 (灰蓝)
    {
        juce::Path bgArc;
        bgArc.addCentredArc(centre.x, centre.y,
            arcRadius, arcRadius, 0.0f,
            rotaryStartAngle, rotaryEndAngle, true);
        g.setColour(UITheme::trackBg);
        g.strokePath(bgArc, juce::PathStrokeType(lineW, juce::PathStrokeType::curved, juce::PathStrokeType::rounded));
    }

    // 已调节值 Arc
    const float toAngle = rotaryStartAngle + sliderPosProportional * (rotaryEndAngle - rotaryStartAngle);
    {
        juce::Path valueArc;
        valueArc.addCentredArc(centre.x, centre.y,
            arcRadius, arcRadius, 0.0f,
            rotaryStartAngle, toAngle, true);

        juce::Colour base = slider.isEnabled() ? UITheme::accentBase : UITheme::accentDisabled;
        // 可叠加轻微渐变（从高亮 → 基色）
        juce::Colour brighter = base.brighter(0.35f);
        juce::ColourGradient grad(brighter, centre.x, centre.y - arcRadius * 0.7f,
            base, centre.x, centre.y + arcRadius * 0.7f, false);
        g.setGradientFill(grad);
        g.strokePath(valueArc, juce::PathStrokeType(lineW, juce::PathStrokeType::curved, juce::PathStrokeType::rounded));
    }

    // 旋钮主体（帽子）
    const float knobRadius = arcRadius - lineW * 1.4f;
    {
        juce::ColourGradient capGrad(UITheme::capHighlight, centre.x, centre.y - knobRadius * 0.6f,
            UITheme::capShade, centre.x, centre.y + knobRadius, true);
        g.setGradientFill(capGrad);
        g.fillEllipse(centre.x - knobRadius, centre.y - knobRadius, knobRadius * 2.0f, knobRadius * 2.0f);

        // 外圈柔和边框
        g.setColour(UITheme::borderSoft.withAlpha(0.9f));
        g.drawEllipse(centre.x - knobRadius, centre.y - knobRadius, knobRadius * 2.0f, knobRadius * 2.0f, 1.0f);

        // 顶部高光弧
        juce::Path highlight;
        auto highlightRadius = knobRadius - 1.5f;
        highlight.addCentredArc(centre.x, centre.y,
            highlightRadius, highlightRadius, 0.0f,
            juce::degreesToRadians(210.0f),
            juce::degreesToRadians(330.0f), false);
        g.setColour(juce::Colours::white.withAlpha(0.22f));
        g.strokePath(highlight, juce::PathStrokeType(1.2f));
    }

    // 指针（刻度线）
    {
        const float pointerOuter = knobRadius * 0.92f;
        const float pointerInner = knobRadius * 0.45f;
        juce::Point<float> pOut = centre.getPointOnCircumference(pointerOuter, toAngle);
        juce::Point<float> pIn = centre.getPointOnCircumference(pointerInner, toAngle);

        g.setColour(UITheme::accentActive);
        g.drawLine({ pIn, pOut }, 2.0f);

        // 指针端点小圆
        g.setColour(UITheme::accentBright.withAlpha(0.85f));
        g.fillEllipse(pOut.x - 3.0f, pOut.y - 3.0f, 6.0f, 6.0f);
    }

    // 若禁用，加一层半透明蒙版
    if (!slider.isEnabled())
    {
        g.setColour(UITheme::surfaceBg.withAlpha(0.35f));
        g.fillEllipse(centre.x - knobRadius, centre.y - knobRadius, knobRadius * 2.0f, knobRadius * 2.0f);
    }
}

// ================= 按钮背景 =================
void PluginLookAndFeel::drawButtonBackground(juce::Graphics& g,
    juce::Button& button,
    const juce::Colour& /*backgroundColour*/,
    bool isMouseOverButton,
    bool isButtonDown)
{
    auto bounds = button.getLocalBounds().toFloat();
    const float corner = juce::jmin(6.0f, bounds.getHeight() / 2.0f);

    bool enabled = button.isEnabled();
    bool primary = isPrimaryButton(button);

    juce::Colour base;

    if (primary)
    {
        // 主按钮使用强调色块
        base = UITheme::accentBase;
        if (!enabled) base = UITheme::accentDisabled;
        else if (isButtonDown) base = UITheme::accentActive;
        else if (isMouseOverButton) base = UITheme::accentHover;
    }
    else
    {
        // 次级按钮：浅面板 + 渐变
        base = UITheme::controlBase;
        if (!enabled)
            base = UITheme::controlBase.withMultipliedAlpha(0.45f);
        else if (isButtonDown)
            base = UITheme::controlBase.darker(0.15f);
        else if (isMouseOverButton)
            base = UITheme::controlBase.brighter(0.10f);
    }

    // 渐变（次级按钮较明显；主按钮轻微）
    juce::Colour top = primary ? base.brighter(0.12f) : base.brighter(0.20f);
    juce::Colour bottom = primary ? base.darker(0.10f) : base.darker(0.05f);

    juce::ColourGradient bgGrad(top, bounds.getCentreX(), bounds.getY(),
        bottom, bounds.getCentreX(), bounds.getBottom(), false);
    g.setGradientFill(bgGrad);
    g.fillRoundedRectangle(bounds, corner);

    // 内发光（Hover 状态 或 Primary）
    if (enabled && !isButtonDown)
    {
        float alpha = primary ? 0.35f : (isMouseOverButton ? 0.28f : 0.18f);
        g.setColour(juce::Colours::white.withAlpha(alpha));
        g.drawRoundedRectangle(bounds.reduced(0.6f), corner - 0.6f, 1.0f);
    }

    // 边框
    juce::Colour border = primary ? base.darker(0.35f) : UITheme::borderSoft.darker(0.15f);
    if (!enabled) border = border.withAlpha(0.35f);
    g.setColour(border.withAlpha(0.9f));
    g.drawRoundedRectangle(bounds.reduced(0.5f), corner - 0.5f, 1.0f);

    // 焦点环
    if (button.hasKeyboardFocus(false))
    {
        juce::Path focusOutline;
        auto fr = bounds.expanded(2.5f);
        focusOutline.addRoundedRectangle(fr, corner + 2.0f);
        g.setColour(UITheme::focusRing.withAlpha(0.55f));
        g.strokePath(focusOutline, juce::PathStrokeType(2.0f));
    }
}

// ================= 按钮文字 =================
void PluginLookAndFeel::drawButtonText(juce::Graphics& g,
    juce::TextButton& button,
    bool /*isMouseOverButton*/,
    bool /*isButtonDown*/)
{
    juce::Font font(14.0f, juce::Font::bold);
    g.setFont(font);

    juce::Colour textCol;
    if (!button.isEnabled())
        textCol = UITheme::textDisabled;
    else
        textCol = UITheme::textMain; // 统一使用深色文字

    g.setColour(textCol);

    auto bounds = button.getLocalBounds().toFloat();
    g.drawFittedText(button.getButtonText(),
        bounds.toNearestInt(),
        juce::Justification::centred, 1);
}


// ================= 滑块文字框（如果你使用 TextBox） =================
juce::Label* PluginLookAndFeel::createSliderTextBox(juce::Slider& slider)
{
    auto* l = juce::LookAndFeel_V4::createSliderTextBox(slider);
    if (l != nullptr)
    {
        l->setColour(juce::Label::backgroundColourId, UITheme::panelBg);
        l->setColour(juce::Label::textColourId, UITheme::textMain);
        l->setColour(juce::Label::outlineColourId, UITheme::borderSoft);
        l->setJustificationType(juce::Justification::centred);
    }
    return l;
}

// ================= 复选框 / ToggleButton（可选） =================
void PluginLookAndFeel::drawToggleButton(juce::Graphics& g,
    juce::ToggleButton& button,
    bool isMouseOverButton,
    bool isButtonDown)
{
    auto bounds = button.getLocalBounds();
    auto box = bounds.removeFromLeft(juce::jmin(bounds.getHeight(), 18)).toFloat().reduced(2);

    // 盒子
    juce::Colour boxFill = UITheme::controlBase;
    if (!button.isEnabled()) boxFill = boxFill.withMultipliedAlpha(0.5f);
    else if (isButtonDown) boxFill = boxFill.darker(0.15f);
    else if (isMouseOverButton) boxFill = boxFill.brighter(0.08f);

    g.setColour(boxFill);
    g.fillRoundedRectangle(box, 3.0f);
    g.setColour(UITheme::borderSoft.darker(0.2f));
    g.drawRoundedRectangle(box, 3.0f, 1.0f);

    // 状态勾 / 圆点
    if (button.getToggleState())
    {
        g.setColour(UITheme::accentBase);
        g.fillEllipse(box.reduced(4.0f));
    }

    // 文字
    g.setFont(juce::Font(14.0f));
    juce::Colour txt = button.isEnabled() ? UITheme::textMain : UITheme::textDisabled;
    g.setColour(txt);
    g.drawFittedText(button.getButtonText(), bounds, juce::Justification::centredLeft, 1);
}

// ================= 额外：PopupMenu 分割线 =================
void PluginLookAndFeel::drawPopupMenuSectionHeader(juce::Graphics& g,
    const juce::Rectangle<int>& area,
    const juce::String& sectionName)
{
    //g.setColour(UITheme::textSubtle.withAlpha(0.8f));
    g.setColour(UITheme::textMain);
    g.setFont(juce::Font(12.0f, juce::Font::bold));
    g.drawFittedText(sectionName.toUpperCase(), area, juce::Justification::centredLeft, 1);

    juce::Rectangle<int> lineArea = area;
    lineArea.removeFromTop(area.getHeight() - 4);
    g.setColour(UITheme::textMain);
    g.fillRect(lineArea);
}
// ================= Tab 宽度控制 =================
int PluginLookAndFeel::getTabButtonBestWidth(juce::TabBarButton& button, int tabDepth)
{
    // tabDepth 是 Tab 高度（水平布局时），可用来决定字体大小
    // 这里我们固定一个字体（你可根据 tabDepth 自适应）
    juce::Font font(juce::jmin(14.0f, (float)tabDepth * 0.55f), juce::Font::bold);

    auto text = button.getButtonText();
    int textW = (int)std::ceil(font.getStringWidthFloat(text));
    int padding = 26;                        // 基础左右内边距总量
    int base = juce::jmax(70, textW + padding); // 最小 70

    // 通过索引获取 Tab 次序
    auto& bar = button.getTabbedButtonBar();
    int index = bar.indexOfTabButton(&button);
    int numTabs = bar.getNumTabs(); // 获取当前标签总数（应该是6个）

    // -------------------- 开关（按需修改） --------------------
    constexpr bool useUniformWidth = true;    // 设为 true 则全部等宽（关键修改）
    constexpr bool useRatioMode = false;      // 保持关闭，让等宽模式生效
    // ---------------------------------------------------------

    // 1) 比例模式：给 5 个标签按百分比分配一个基础参考宽度
    if (useRatioMode)
    {
        // 原比例模式代码保持不变
        static const float ratios[] = { 0.20f, 0.24f, 0.22f, 0.22f, 0.12f }; // 和 = 1
        if (numTabs == 5)
        {
            float totalReference = 600.0f;
            return (int)std::round(totalReference * ratios[index]);
        }
    }

    // 2) 统一等宽模式（关键修改：按800总宽度平均分配）
    if (useUniformWidth)
    {
        // 总宽度800除以标签数量（6个），得到每个标签的平均宽度
        // 减1是为了预留微小间距，避免总宽度超出
        return 800 / numTabs - 1;
    }

    // 3) 按名称 / 索引微调（当前模式下不会执行）
    if (text == "Pedals")        return base + 30;
    if (text == "Amplifier")     return base + 40;
    if (text == "Cabinet")       return base + 10;
    if (text == "Mixer")         return base;
    if (text == "Hidden")        return 60;
    if (text == "Chat")          return base + 20;

    // 4) 按索引调整（当前模式下不会执行）
    switch (index)
    {
    case 0: /* Pedals */    return base + 30;
    case 1: /* Amplifier */ return base + 40;
    case 2: /* Cabinet */   return base + 10;
    case 3: /* Mixer */     return base;
    case 4: /* Hidden */    return 60;
    default:                break;
    }

    return base;
}

void PluginLookAndFeel::positionComboBoxText(juce::ComboBox& box, juce::Label& label)
{
    // 先让基类完成布局（尺寸、对齐）
    LookAndFeel_V4::positionComboBoxText(box, label);

    // “未选择”判定：JUCE 里未选择时 selectedId == 0
    const bool noSelection = (box.getSelectedId() == 0);

    // 正常文本颜色：用 ComboBox::textColourId（你外部已经 setColour 了）
    auto normalColour = juce::Colour::fromRGB(0x00, 0x00, 0x00);

    // 占位颜色：如果你在 UITheme 里加了 comboPlaceholder 就用它；否则用 textDisabled 或自行调和
    auto placeholderColour = UITheme::comboPlaceholder;
    // 备选写法（若未添加 comboPlaceholder 定义）:
    // auto placeholderColour = UITheme::textDisabled.withAlpha(0.90f);
    // 或更淡一些：
    // auto placeholderColour = normalColour.withAlpha(0.45f);

    label.setColour(juce::Label::textColourId,
        noSelection ? placeholderColour : normalColour);

    // 可选：占位用斜体 / 普通用常规
    label.setFont(label.getFont().withStyle(noSelection
        ? juce::Font::italic
        : juce::Font::plain));
}
