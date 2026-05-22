import { useState, useCallback } from 'react';

export interface UseWizardOptions {
  steps: string[];
  validateStep?: (stepIndex: number) => boolean;
  initialStep?: number;
}

export interface UseWizardReturn {
  currentStepIndex: number;
  currentStepName: string;
  nextStep: () => void;
  prevStep: () => void;
  goToStep: (index: number) => void;
  isFirst: boolean;
  isLast: boolean;
  totalSteps: number;
}

/**
 * useWizard - Wizard逻辑Hook
 * 管理多步骤向导的导航和验证
 */
export const useWizard = ({
  steps,
  validateStep,
  initialStep = 0,
}: UseWizardOptions): UseWizardReturn => {
  const [currentStepIndex, setCurrentStepIndex] = useState<number>(
    Math.max(0, Math.min(initialStep, steps.length - 1))
  );

  const nextStep = useCallback(() => {
    if (currentStepIndex < steps.length - 1) {
      // 如果提供了验证函数，先验证当前步骤
      if (validateStep) {
        const isValid = validateStep(currentStepIndex);
        if (!isValid) {
          return; // 验证失败，阻止前进
        }
      }
      setCurrentStepIndex(currentStepIndex + 1);
    }
  }, [currentStepIndex, steps.length, validateStep]);

  const prevStep = useCallback(() => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(currentStepIndex - 1);
    }
  }, [currentStepIndex]);

  const goToStep = useCallback(
    (index: number) => {
      const targetIndex = Math.max(0, Math.min(index, steps.length - 1));
      setCurrentStepIndex(targetIndex);
    },
    [steps.length]
  );

  const isFirst = currentStepIndex === 0;
  const isLast = currentStepIndex === steps.length - 1;
  const currentStepName = steps[currentStepIndex] || '';

  return {
    currentStepIndex,
    currentStepName,
    nextStep,
    prevStep,
    goToStep,
    isFirst,
    isLast,
    totalSteps: steps.length,
  };
};


