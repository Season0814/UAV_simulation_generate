# Micro-Agent Prompt Example: Inertial Agent

This document illustrates how the main agent dynamically constructs a highly constrained prompt for the `Inertial Agent` by combining the static template rules with the dynamic user description (Short-Term Memory).

## The Constructed Prompt ($Prompt_{ik}$)

```text
You are an expert SDF (Simulation Description Format) generator.
Your task is to generate an XML component based on the user's description and the provided template.

User Description: 
Generate an inertial component with the following specifications:
Inertial: Base Link
Default mass: 1.5
Default ixx, iyy: 0.015, izz: 0.02
User overrides (take precedence over defaults):
{"mass": 3.5, "ixx": 0.035, "iyy": 0.035, "izz": 0.065}

Template:
<inertial>
  <mass>${mass}</mass>
  <inertia>
    <ixx>${ixx}</ixx>
    <ixy>${ixy}</ixy>
    <ixz>${ixz}</ixz>
    <iyy>${iyy}</iyy>
    <iyz>${iyz}</iyz>
    <izz>${izz}</izz>
  </inertia>
</inertial>

Instructions:
1. Analyze the description to extract values for the placeholders in the template (e.g., ${visualName}, ${pose}, ${size}).
2. Fill in the template with the extracted values.
3. Check the provided template for a 'Defaults' section (usually in comments). If a value is not explicitly provided in the User Description, use the value from the Defaults section.
4. Output ONLY the filled XML content. Do not include markdown formatting or explanations.

Output XML:
```

## The Micro-Agent's Output ($\mathcal{F}_i$)

Because the prompt strictly constraints the LLM to output ONLY the filled XML, and limits its context to purely inertial data, the micro-agent returns exactly what is required without any hallucinations:

```xml
<inertial>
  <mass>3.5</mass>
  <inertia>
    <ixx>0.035</ixx>
    <ixy>0.0</ixy>
    <ixz>0.0</ixz>
    <iyy>0.035</iyy>
    <iyz>0.0</iyz>
    <izz>0.065</izz>
  </inertia>
</inertial>
```
